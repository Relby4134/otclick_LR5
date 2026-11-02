from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from .models import Survey, Response, Answer
from .forms import SurveyForm
from .services import build_answer, public_summary

def index(request):
    surveys = list(Survey.objects.filter(is_active=True))
    for survey in surveys:
        survey.public_summary = public_summary(survey)
    return render(request, 'surveys/index.html', {'surveys': surveys})

def detail(request, pk):
    survey = get_object_or_404(Survey,pk=pk,is_active=True)
    questions = list(survey.questions.prefetch_related('choices'))
    form = SurveyForm(request.POST if request.method == 'POST' else None, questions=questions)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            response = Response.objects.create(survey=survey)
            answers = [build_answer(response, q, form.cleaned_data[f'q_{q.pk}']) for q in questions]
            Answer.objects.bulk_create(answers)
            response.graded_count = sum(a.is_correct is not None for a in answers)
            response.score = sum(a.is_correct is True for a in answers) if response.graded_count else None
            response.save(update_fields=['score', 'graded_count'])
        request.session.pop('response_ids', None)
        request.session['last_response_id'] = response.pk
        return redirect('thanks')
    return render(request,'surveys/detail.html',{'survey':survey,'summary':public_summary(survey),'rows':[(q,form[f'q_{q.pk}']) for q in questions]})


def thanks(request):
    response = Response.objects.select_related('survey').filter(pk=request.session.get('last_response_id')).first()
    context = {'survey': response.survey, 'summary': public_summary(response.survey)} if response else {}
    return render(request, 'surveys/thanks.html', context)


def response_detail(request, pk):
    # Old links remain usable for administrators only.
    from django.http import Http404
    if not request.user.is_staff:
        raise Http404
    get_object_or_404(Response, pk=pk)
    return redirect('admin:surveys_response_change', pk)


@staff_member_required
def results(request, pk):
    get_object_or_404(Survey, pk=pk)
    return redirect('admin:surveys_survey_statistics', pk)
