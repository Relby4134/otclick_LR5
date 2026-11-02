from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Survey, Question, Choice, Response
from django.core.management import call_command
from io import StringIO

class SurveyTests(TestCase):
    def setUp(self):
        self.survey = Survey.objects.create(title='Demo')
        self.image = Question.objects.create(survey=self.survey,title='Image',kind='image')
        self.choice = Choice.objects.create(question=self.image,label='Sea',image_url='/static/surveys/sea.svg')
        self.slider = Question.objects.create(survey=self.survey,title='Score',kind='slider',minimum=0,maximum=10)
        self.url = f'/surveys/{self.survey.pk}/'
    def test_render_and_submit(self):
        page = self.client.get(self.url)
        self.assertContains(page,'/static/surveys/sea.svg')
        self.assertContains(page,'type="range"')
        result = self.client.post(self.url,{f'q_{self.image.pk}':self.choice.pk,f'q_{self.slider.pk}':7})
        self.assertRedirects(result,'/thanks/')
        self.assertEqual(Response.objects.count(),1)
        self.assertEqual(Response.objects.first().answers.count(),2)
    def test_invalid_submission_creates_no_response(self):
        for payload in [{},{f'q_{self.image.pk}':999,f'q_{self.slider.pk}':7},{f'q_{self.image.pk}':self.choice.pk,f'q_{self.slider.pk}':11}]:
            self.assertEqual(self.client.post(self.url,payload).status_code,200)
        self.assertEqual(Response.objects.count(),0)
    def test_results_are_staff_only(self):
        url = self.url+'results/'
        self.assertEqual(self.client.get(url).status_code,302)
        user = get_user_model().objects.create_user(username='reviewer',is_staff=True)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(url), f'/admin/surveys/survey/{self.survey.pk}/statistics/', fetch_redirect_response=False)
    def test_inactive_survey_is_unavailable(self):
        self.survey.is_active=False
        self.survey.save()
        self.assertEqual(self.client.get(self.url).status_code,404)


class AdminAndGradingTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='admin', password='test-password', email='admin@example.com')
        self.survey = Survey.objects.create(title='Quiz', is_quiz=True)
        self.question = Question.objects.create(survey=self.survey, title='Choose', kind='multiple')
        self.right = Choice.objects.create(question=self.question, label='Right', is_correct=True)
        self.wrong = Choice.objects.create(question=self.question, label='Wrong')
    def submit(self, choices):
        self.client.post(f'/surveys/{self.survey.pk}/', {f'q_{self.question.pk}': choices})
        return Response.objects.first()
    def test_exact_match_and_snapshot(self):
        response = self.submit([str(self.right.pk)])
        self.assertEqual((response.score,response.graded_count),(1,1))
        answer = response.answers.get()
        self.right.label='Changed'
        self.right.is_correct=False
        self.right.save()
        answer.refresh_from_db()
        self.assertEqual(answer.readable_value(),'Right')
        self.assertTrue(answer.is_correct)
    def test_extra_selection_is_wrong(self):
        response = self.submit([str(self.right.pk),str(self.wrong.pk)])
        self.assertEqual(response.score,0)
    def test_unconfigured_question_is_not_graded(self):
        self.right.is_correct=False
        self.right.save()
        response=self.submit([str(self.right.pk)])
        self.assertIsNone(response.score)
        self.assertEqual(response.graded_count,0)
    def test_admin_pages_and_answers(self):
        response=self.submit([str(self.right.pk)])
        self.client.force_login(self.admin)
        for url in ['/admin/','/admin/surveys/survey/', '/admin/surveys/response/', f'/admin/surveys/survey/{self.survey.pk}/change/', f'/admin/surveys/survey/{self.survey.pk}/statistics/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
        self.assertContains(self.client.get(f'/admin/surveys/response/{response.pk}/change/'),'Right')
        self.assertContains(self.client.get(f'/admin/surveys/survey/{self.survey.pk}/statistics/'),'100')
    def test_statistics_requires_survey_permission(self):
        url=f'/admin/surveys/survey/{self.survey.pk}/statistics/'
        self.assertEqual(self.client.get(url).status_code,302)
        staff=get_user_model().objects.create_user(username='limited',is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code,403)


class DemoQuizTests(TestCase):
    def test_demo_quizzes_are_repeatable_and_grade_submissions(self):
        for _ in range(2):
            call_command('seed_quizzes', stdout=StringIO())
        quizzes = Survey.objects.filter(is_quiz=True)
        self.assertEqual(quizzes.count(), 2)
        self.assertEqual(Question.objects.count(), 10)
        for quiz in quizzes:
            questions = list(quiz.questions.all())
            correct_payload = {}
            wrong_payload = {}
            for question in questions:
                correct = list(question.choices.filter(is_correct=True).values_list('pk', flat=True))
                wrong = str(question.choices.filter(is_correct=False).first().pk)
                self.assertTrue(correct)
                key = f'q_{question.pk}'
                correct_payload[key] = [str(pk) for pk in correct] if question.kind == 'multiple' else str(correct[0])
                wrong_payload[key] = [wrong] if question.kind == 'multiple' else wrong
            url = f'/surveys/{quiz.pk}/'
            self.assertRedirects(self.client.post(url, correct_payload), '/thanks/')
            response = quiz.responses.first()
            self.assertEqual((response.score, response.graded_count), (5, 5))
            self.assertRedirects(self.client.post(url, wrong_payload), '/thanks/')
            response = quiz.responses.first()
            self.assertEqual((response.score, response.graded_count), (0, 5))


class InteractiveResultTests(TestCase):
    def setUp(self):
        call_command('seed_interactive', stdout=StringIO())
        self.quiz = Survey.objects.get(title='Основы Python')
        self.url = f'/surveys/{self.quiz.pk}/'
    def payload(self, correct=True):
        data = {}
        for q in self.quiz.questions.all():
            key = f'q_{q.pk}'
            if q.kind == 'slider':
                data[key] = q.correct_number if correct else q.maximum
            elif q.kind == 'audio':
                data[key] = '  sos!  ' if correct else 'ABC'
            else:
                options = list(q.choices.filter(is_correct=correct).values_list('pk',flat=True))
                data[key] = [str(v) for v in options] if q.kind == 'multiple' else str(options[0])
        return data
    def test_full_interactive_score_and_review(self):
        call_command('seed_interactive', stdout=StringIO())
        self.assertEqual(self.quiz.questions.count(),8)
        page=self.client.get(self.url)
        self.assertContains(page,'<audio')
        self.assertContains(page,'/static/surveys/triangle.svg')
        self.assertContains(page,'type="range"')
        self.assertNotContains(page,'Правильное значение ползунка')
        self.assertRedirects(self.client.post(self.url,self.payload()),'/thanks/')
        response=self.quiz.responses.first()
        self.assertEqual((response.score,response.graded_count),(8,8))
        review=self.client.get('/thanks/')
        self.assertContains(review,'100%')
        self.assertNotContains(review,'Правильный ответ')
        self.assertNotContains(review,'SOS')
        self.assertNotContains(review,'Выберите картинку')
    def test_wrong_answers_and_saved_key(self):
        self.client.post(self.url,self.payload(False))
        response=self.quiz.responses.first()
        self.assertEqual((response.score,response.graded_count),(0,8))
        slider=response.answers.get(question__kind='slider')
        self.assertEqual(slider.correct_value,'4')
        slider.question.correct_number=9
        slider.question.save()
        slider.refresh_from_db()
        self.assertEqual(slider.correct_value,'4')
        review=self.client.get('/thanks/')
        self.assertContains(review,'0%')
        self.assertNotContains(review,'Неверных ответов')
        self.assertNotContains(review,'✕ Неверно')
    def test_response_privacy_and_staff_summary(self):
        self.client.post(self.url,self.payload())
        response=self.quiz.responses.first()
        url=f'/responses/{response.pk}/'
        self.assertEqual(self.client.get(url).status_code,404)
        from django.test import Client
        self.assertEqual(Client().get(url).status_code,404)
        staff=get_user_model().objects.create_user(username='reporter',is_staff=True)
        self.client.force_login(staff)
        summary=self.client.get(f'/surveys/{self.quiz.pk}/results/')
        self.assertRedirects(summary, f'/admin/surveys/survey/{self.quiz.pk}/statistics/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get(url), f'/admin/surveys/response/{response.pk}/change/', fetch_redirect_response=False)
    def test_plain_survey_shows_readable_answers_without_score(self):
        survey=Survey.objects.create(title='Обычный опрос')
        question=Question.objects.create(survey=survey,title='Ваше мнение',kind='text')
        self.client.post(f'/surveys/{survey.pk}/',{f'q_{question.pk}':'Мне нравится'})
        page=self.client.get('/thanks/')
        self.assertContains(page,'Ваши ответы сохранены')
        self.assertContains(page,'раз прошли этот опрос')
        self.assertNotContains(page,'Ваше мнение')
        self.assertNotContains(page,'Мне нравится')
        self.assertNotContains(page,'Неверных ответов')
    def test_numeric_key_must_be_in_range(self):
        from django.core.exceptions import ValidationError
        question=self.quiz.questions.get(kind='slider')
        question.correct_number=99
        with self.assertRaises(ValidationError): question.full_clean()


class PublicSummaryTests(TestCase):
    def test_pass_rate_excludes_ungraded_and_handles_zero(self):
        from .services import public_summary
        survey=Survey.objects.create(title='Summary',is_quiz=True)
        self.assertIsNone(public_summary(survey)['success_percent'])
        Response.objects.create(survey=survey,score=4,graded_count=5)
        Response.objects.create(survey=survey,score=3,graded_count=5)
        Response.objects.create(survey=survey,score=None,graded_count=0)
        self.assertEqual(public_summary(survey)['success_percent'],50)
        self.assertEqual(public_summary(survey)['total'],2)
        survey.pass_percent=60
        survey.save()
        self.assertEqual(public_summary(survey)['success_percent'],100)
        self.assertContains(self.client.get('/'),'100%')
        self.assertNotContains(self.client.get('/'),'Результаты')
    def test_detailed_stats_live_in_admin(self):
        survey=Survey.objects.create(title='Stats',is_quiz=True)
        question=Question.objects.create(survey=survey,title='Private question',kind='single')
        choice=Choice.objects.create(question=question,label='Private answer',is_correct=True)
        self.client.post(f'/surveys/{survey.pk}/',{f'q_{question.pk}':str(choice.pk)})
        response=survey.responses.first()
        self.assertNotContains(self.client.get('/thanks/'),'Private answer')
        self.assertEqual(self.client.get(f'/responses/{response.pk}/').status_code,404)
        user=get_user_model().objects.create_superuser(username='stats-admin',password='test-password',email='stats@example.com')
        self.client.force_login(user)
        page=self.client.get(f'/admin/surveys/survey/{survey.pk}/statistics/')
        self.assertContains(page,'Верных ответов')
        self.assertContains(page,'Неверных ответов')
        self.assertContains(page,'Private question')
        self.assertContains(page,'100%')
        page=self.client.get(f'/admin/surveys/response/{response.pk}/change/')
        self.assertContains(page,'Private answer')
        self.assertContains(page,'Правильный ответ на момент прохождения')


class PuzzleTests(TestCase):
    def setUp(self):
        import base64
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        self.media = tempfile.TemporaryDirectory(prefix='survey-puzzle-tests-')
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        image = SimpleUploadedFile('test.png', base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='), content_type='image/png')
        self.survey = Survey.objects.create(title='Puzzle quiz', is_quiz=True)
        self.question = Question.objects.create(survey=self.survey, title='Совместите фрагмент', kind='puzzle', puzzle_image=image, puzzle_target=65, puzzle_tolerance=3)
        self.url = f'/surveys/{self.survey.pk}/'
    def test_submission_tolerance_and_snapshot(self):
        key=f'q_{self.question.pk}'
        for value, expected in [(62,True),(68,True),(61,False),(69,False),(65,True),(0,False),(100,False)]:
            self.assertRedirects(self.client.post(self.url,{key:value}),'/thanks/')
            answer=self.survey.responses.first().answers.get()
            self.assertEqual(answer.is_correct,expected)
            self.assertEqual(answer.correct_value,'Положение 65 из 100, погрешность ±3')
            self.assertEqual(answer.display_value,f'Положение {value} из 100')
        self.question.puzzle_target=20
        self.question.save()
        self.assertEqual(answer.correct_value,'Положение 65 из 100, погрешность ±3')
    def test_invalid_input_is_not_saved(self):
        for value in [-1,101,'abc','']:
            self.assertEqual(self.client.post(self.url,{f'q_{self.question.pk}':value}).status_code,200)
        self.assertEqual(self.survey.responses.count(),0)
    def test_render_and_bound_value(self):
        page=self.client.get(self.url)
        self.assertContains(page,'data-puzzle')
        self.assertContains(page,self.question.puzzle_image.url)
        self.assertContains(page,'surveys/puzzle.css')
        other=Question.objects.create(survey=self.survey,title='Required text',kind='text')
        page=self.client.post(self.url,{f'q_{self.question.pk}':44})
        self.assertContains(page,'value="44"')
        self.assertNotContains(page,'Правильный ответ')
    def test_non_quiz_and_optional_puzzle(self):
        self.survey.is_quiz=False
        self.survey.save()
        self.question.required=False
        self.question.save()
        self.client.post(self.url,{})
        response=self.survey.responses.first()
        self.assertIsNone(response.score)
        self.assertEqual(response.answers.get().display_value,'Без ответа')
    def test_puzzle_configuration_requires_image_and_valid_coordinates(self):
        from django.core.exceptions import ValidationError
        question=Question(survey=self.survey,title='No image',kind='puzzle')
        with self.assertRaises(ValidationError): question.full_clean()
        self.question.puzzle_target=101
        with self.assertRaises(ValidationError): self.question.full_clean()
    def test_admin_preview_and_image_validation(self):
        user=get_user_model().objects.create_superuser(username='puzzle-admin',password='test-password',email='puzzle@example.com')
        self.client.force_login(user)
        page=self.client.get(f'/admin/surveys/question/{self.question.pk}/change/')
        self.assertContains(page,'data-puzzle')
        self.assertContains(page,'multipart/form-data')
        self.assertContains(page,'surveys/app.js')
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.forms import modelform_factory
        form_class=modelform_factory(Question,fields=['survey','title','kind','puzzle_image'])
        form=form_class(data={'survey':self.survey.pk,'title':'Bad upload','kind':'puzzle'}, files={'puzzle_image':SimpleUploadedFile('bad.png',b'not-an-image',content_type='image/png')})
        self.assertFalse(form.is_valid())
        self.assertIn('puzzle_image',form.errors)
        with self.question.puzzle_image.open('rb') as stored:
            image=SimpleUploadedFile('valid.png',stored.read(),content_type='image/png')
        valid=form_class(data={'survey':self.survey.pk,'title':'Good upload','kind':'puzzle'},files={'puzzle_image':image})
        self.assertTrue(valid.is_valid(),valid.errors)



class AuthoringFlowTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_superuser(username='author',password='test-password',email='author@example.com')
        self.client.force_login(self.user)
        self.survey=Survey.objects.create(title='Draft',is_active=False)
    def test_navigation_order_and_survey_creation(self):
        page=self.client.get('/admin/')
        names=[m['object_name'] for app in page.context['app_list'] if app['app_label']=='surveys' for m in app['models']]
        self.assertEqual(names,['Survey','Question','Response'])
        page=self.client.get('/admin/surveys/survey/add/')
        self.assertFalse(page.context['adminform'].form['is_active'].value())
        self.assertNotContains(page,'id_questions-TOTAL_FORMS')
        response=self.client.post('/admin/surveys/survey/add/',{'title':'New survey','description':'Draft content','pass_percent':80,'_save':'1'})
        survey=Survey.objects.get(title='New survey')
        self.assertRedirects(response,f'/admin/surveys/survey/{survey.pk}/change/')
        self.assertFalse(survey.is_active)
        page=self.client.get(response.url)
        self.assertContains(page,f'/admin/surveys/question/add/?survey={survey.pk}')
    def test_add_question_from_survey_and_return(self):
        question=Question.objects.create(survey=self.survey,title='Existing',kind='text',order=3)
        page=self.client.get(f'/admin/surveys/question/add/?survey={self.survey.pk}')
        self.assertEqual(str(page.context['adminform'].form['survey'].value()),str(self.survey.pk))
        self.assertEqual(page.context['adminform'].form['order'].value(),4)
        data={'survey':self.survey.pk,'title':'New question','kind':'text','required':'on','order':4,'minimum':0,'maximum':10,'puzzle_target':65,'puzzle_y':50,'puzzle_tolerance':3,'choices-TOTAL_FORMS':0,'choices-INITIAL_FORMS':0,'_save':'1'}
        response=self.client.post(f'/admin/surveys/question/add/?survey={self.survey.pk}',data)
        self.assertRedirects(response,f'/admin/surveys/survey/{self.survey.pk}/change/')
        self.assertTrue(self.survey.questions.filter(title='New question').exists())
    def test_draft_preview_is_read_only_and_requires_permission(self):
        Question.objects.create(survey=self.survey,title='Preview-only question',kind='text')
        url=f'/admin/surveys/survey/{self.survey.pk}/preview/'
        page=self.client.get(url)
        self.assertContains(page,'Preview-only question')
        self.assertNotContains(page,'Отправить ответы')
        self.assertEqual(self.client.post(url,{}).status_code,405)
        self.assertEqual(self.survey.responses.count(),0)
        self.assertEqual(self.client.get(f'/surveys/{self.survey.pk}/').status_code,404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code,302)
        staff=get_user_model().objects.create_user(username='limited-preview',is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code,403)
    def test_editor_available_before_first_save(self):
        page=self.client.get(f'/admin/surveys/question/add/?survey={self.survey.pk}')
        self.assertContains(page,'data-puzzle-editor')
        self.assertContains(page,'surveys/admin-editor.js')
        self.assertContains(page,'question-puzzle')
        self.assertContains(page,'question-audio')
        self.assertContains(page,'question-slider')

    def test_continue_adding_keeps_parent_survey(self):
        data={'survey':self.survey.pk,'title':'Another question','kind':'text','order':1,'minimum':0,'maximum':10,'puzzle_target':65,'puzzle_y':50,'puzzle_tolerance':3,'_addanother':'1'}
        response=self.client.post('/admin/surveys/question/add/',data)
        self.assertRedirects(response,f'/admin/surveys/question/add/?survey={self.survey.pk}')
