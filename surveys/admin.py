from django.contrib import admin
from django.db.models import Count
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.db.models import Max
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.template.loader import render_to_string
from .models import Survey, Question, Choice, Response, Answer
from .services import public_summary
from .forms import SurveyForm

admin.site.site_header = 'Отклик · управление опросами'
admin.site.site_title = 'Отклик'
admin.site.index_title = 'Рабочее пространство'

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'survey', 'kind', 'required', 'order']
    list_filter = ['survey', 'kind']
    search_fields = ['title', 'survey__title']
    inlines = [ChoiceInline]
    change_form_template = 'admin/surveys/question/change_form.html'
    readonly_fields = ['puzzle_preview']
    fieldsets = [('Вопрос', {'fields': ('survey', 'title', 'kind', 'required', 'order')}),
        ('Пазл с ползунком', {'fields': ('puzzle_image', 'puzzle_target', 'puzzle_y', 'puzzle_tolerance', 'puzzle_preview'),
            'classes': ('question-puzzle',),
            'description': 'Загрузите картинку и укажите место фрагмента прямо на изображении. Предпросмотр работает до сохранения.'}),
        ('Настройки ползунка', {'fields': ('minimum', 'maximum', 'correct_number'), 'classes': ('question-slider',)}),
        ('Аудиозапись', {'fields': ('audio_url',), 'classes': ('question-audio',)}),
        ('Проверка текстового ответа', {'fields': ('correct_text',), 'classes': ('question-text',)}),
        ('Объяснение ответа', {'fields': ('explanation',)})]

    class Media:
        css = {'all': ['surveys/puzzle.css?v=3', 'surveys/admin-editor.css?v=2']}
        js = ['surveys/app.js?v=3', 'surveys/admin-editor.js?v=2']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'survey':
            kwargs['label'] = 'Опрос'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inlines(self, request, obj):
        if request.method == 'POST' and request.POST.get('kind') not in ('single', 'multiple', 'image'):
            return []
        return self.inlines

    @admin.display(description='Настройка и предпросмотр')
    def puzzle_preview(self, obj):
        return render_to_string('admin/surveys/question/puzzle_editor.html', {'q': obj})

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        survey_id = request.GET.get('survey', '')
        if survey_id.isdigit():
            maximum = Question.objects.filter(survey_id=survey_id).aggregate(value=Max('order'))['value']
            initial['order'] = (maximum or 0) + 1
        return initial

    def response_add(self, request, obj, post_url_continue=None):
        if '_addanother' in request.POST and '_popup' not in request.POST:
            self.message_user(request, 'Вопрос сохранён. Добавьте следующий вопрос в этот же опрос.')
            return HttpResponseRedirect(reverse('admin:surveys_question_add') + f'?survey={obj.survey_id}')
        if '_save' in request.POST and '_popup' not in request.POST:
            self.message_user(request, 'Вопрос сохранён. Можно добавить следующий или открыть предпросмотр опроса.')
            return HttpResponseRedirect(reverse('admin:surveys_survey_change', args=[obj.survey_id]))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if '_save' in request.POST and '_popup' not in request.POST:
            self.message_user(request, 'Изменения вопроса сохранены.')
            return HttpResponseRedirect(reverse('admin:surveys_survey_change', args=[obj.survey_id]))
        return super().response_change(request, obj)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        survey_id = request.POST.get('survey') or request.GET.get('survey')
        if object_id and str(object_id).isdigit():
            survey_id = Question.objects.filter(pk=object_id).values_list('survey_id', flat=True).first()
        context = {'parent_survey': Survey.objects.filter(pk=survey_id).first() if str(survey_id).isdigit() else None}
        context.update(extra_context or {})
        return super().changeform_view(request, object_id, form_url, context)

class QuestionInline(admin.TabularInline):
    model = Question
    fields = ['edit_question', 'kind_label', 'required', 'order']
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Вопрос')
    def edit_question(self, obj):
        return format_html('<a href="{}">{}</a>', reverse('admin:surveys_question_change', args=[obj.pk]), obj.title)

    @admin.display(description='Тип')
    def kind_label(self, obj):
        return obj.get_kind_display()

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    change_form_template = 'admin/surveys/survey/change_form.html'
    inlines = [QuestionInline]
    list_display = ['title', 'is_active', 'is_quiz', 'response_total', 'statistics_link']
    list_filter = ['is_active', 'is_quiz']
    search_fields = ['title']
    readonly_fields = ['statistics_link']
    fieldsets = [('Об опросе', {'fields': ('title', 'description', 'is_active')}), ('Проверка и результаты', {'fields': ('is_quiz', 'pass_percent', 'statistics_link'), 'description': 'Для тестов отметьте правильные варианты в вопросах. Также можно задать правильное значение ползунка и текстовую расшифровку аудио. Вопросы без ключа остаются без оценки.'})]

    def get_inlines(self, request, obj):
        return self.inlines if obj else []

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial['is_active'] = False
        return initial

    def response_add(self, request, obj, post_url_continue=None):
        if '_save' in request.POST and '_popup' not in request.POST:
            self.message_user(request, 'Опрос создан. Теперь добавьте вопросы.')
            return HttpResponseRedirect(reverse('admin:surveys_survey_change', args=[obj.pk]))
        return super().response_add(request, obj, post_url_continue)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        context = {'can_add_question': self.admin_site._registry[Question].has_add_permission(request)}
        context.update(extra_context or {})
        return super().changeform_view(request, object_id, form_url, context)
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total=Count('responses'))
    @admin.display(description='Прохождений', ordering='total')
    def response_total(self, obj): return obj.total
    @admin.display(description='Статистика')
    def statistics_link(self, obj):
        if not obj.pk: return 'Доступна после сохранения'
        return format_html('<a class="stats-link" href="{}">Смотреть статистику →</a>', reverse('admin:surveys_survey_statistics', args=[obj.pk]))
    def get_urls(self):
        return [path('<int:pk>/statistics/', self.admin_site.admin_view(self.statistics), name='surveys_survey_statistics'),
            path('<int:pk>/preview/', self.admin_site.admin_view(self.preview), name='surveys_survey_preview')] + super().get_urls()

    def preview(self, request, pk):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponseNotAllowed
        if request.method != 'GET':
            return HttpResponseNotAllowed(['GET'])
        survey = get_object_or_404(Survey, pk=pk)
        if not self.has_view_permission(request, survey):
            raise PermissionDenied
        questions = list(survey.questions.prefetch_related('choices'))
        form = SurveyForm(questions=questions)
        return render(request, 'surveys/detail.html', {'survey': survey, 'preview': True,
            'summary': public_summary(survey), 'rows': [(q, form[f'q_{q.pk}']) for q in questions]})
    def statistics(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        if not self.has_view_permission(request, survey):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        responses = list(survey.responses.all())
        graded = [r for r in responses if r.score is not None and r.graded_count]
        rows = []
        for q in survey.questions.prefetch_related('choices'):
            answers = list(Answer.objects.filter(response__survey=survey, question=q))
            values = [a.value for a in answers]
            checked = [a for a in answers if a.is_correct is not None]
            counts = []
            for c in q.choices.all():
                total = sum(str(c.pk) in v if isinstance(v, list) else str(c.pk) == v for v in values)
                counts.append({'label': c.label, 'total': total, 'percent': round(total / len(values) * 100) if values else 0})
            numbers = [v for v in values if isinstance(v, int)]
            rows.append({'question': q, 'counts': counts, 'answers': answers, 'average': round(sum(numbers)/len(numbers), 1) if numbers else None, 'checked': len(checked), 'correct': sum(a.is_correct for a in checked), 'wrong': sum(a.is_correct is False for a in checked)})
        context = dict(self.admin_site.each_context(request), title=f'Статистика: {survey.title}', survey=survey, rows=rows, total=len(responses), graded_total=len(graded), average_score=round(sum(r.score/r.graded_count*100 for r in graded)/len(graded), 1) if graded else None, recent=responses[:10], response_list=reverse('admin:surveys_response_changelist')+f'?survey__id__exact={pk}', opts=self.model._meta)
        context.update(summary=public_summary(survey),
            correct_total=Answer.objects.filter(response__survey=survey, is_correct=True).count(),
            wrong_total=Answer.objects.filter(response__survey=survey, is_correct=False).count())
        return TemplateResponse(request, 'admin/surveys/statistics.html', context)

class AnswerInline(admin.TabularInline):
    model = Answer
    fields = ['question_label', 'answer_label', 'verdict', 'correct_value', 'explanation']
    readonly_fields = fields
    extra = 0
    can_delete = False
    def has_add_permission(self, request, obj=None): return False
    @admin.display(description='Вопрос')
    def question_label(self, obj): return obj.question_title or obj.question.title
    @admin.display(description='Ответ участника')
    def answer_label(self, obj): return obj.readable_value()
    @admin.display(description='Проверка')
    def verdict(self, obj): return 'Без оценки' if obj.is_correct is None else ('Верно' if obj.is_correct else 'Неверно')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'survey', 'created_at', 'result']
    list_filter = ['survey', 'created_at']
    search_fields = ['survey__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['survey', 'created_at', 'result']
    fields = readonly_fields
    inlines = [AnswerInline]
    list_select_related = ['survey']
    @admin.display(description='Результат')
    def result(self, obj):
        return f'{obj.score} из {obj.graded_count} ({obj.score/obj.graded_count:.0%})' if obj.score is not None and obj.graded_count else 'Без оценки'
    def has_add_permission(self, request): return False
