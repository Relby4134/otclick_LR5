from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from surveys.models import Survey, Question, Choice


class Command(BaseCommand):
    help = 'Добавить интерактивные задания в демонстрационные тесты'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        call_command('seed_quizzes', stdout=self.stdout)
        for title in ['Основы Python', 'Основы веб-разработки']:
            survey = Survey.objects.get(title=title)
            question, created = Question.objects.get_or_create(
                survey=survey, title='Выберите картинку с треугольником',
                defaults={'kind': 'image', 'order': 6, 'explanation': 'У треугольника три стороны и три вершины.'},
            )
            if created:
                for label, name, correct in [('Круг', 'circle', False), ('Треугольник', 'triangle', True), ('Квадрат', 'square', False)]:
                    Choice.objects.create(question=question, label=label,
                                          image_url=f'/static/surveys/{name}.svg', is_correct=correct)
            if title == 'Основы Python':
                text, correct, explanation = 'Установите ползунок на результат len([10, 20, 30, 40])', 4, 'len() возвращает количество элементов: в этом списке их четыре.'
            else:
                text, correct, explanation = 'Установите ползунок на количество уровней заголовков HTML (h1–h6)', 6, 'HTML содержит шесть уровней заголовков, от h1 до h6.'
            Question.objects.get_or_create(survey=survey, title=text, defaults={
                'kind': 'slider', 'order': 7, 'minimum': 0, 'maximum': 10,
                'correct_number': correct, 'explanation': explanation,
            })
            Question.objects.get_or_create(survey=survey,
                title='Расшифруйте сигнал Морзе: короткий звук — точка, длинный — тире. Подсказка: S = ···, O = −−−. Введите три латинские буквы.',
                defaults={'kind': 'audio', 'order': 8, 'audio_url': '/static/surveys/morse-sos.wav',
                          'correct_text': 'SOS', 'explanation': 'Три коротких, три длинных и три коротких сигнала образуют SOS.'})
            self.stdout.write(self.style.SUCCESS(f'Интерактивные задания готовы: {title}'))
