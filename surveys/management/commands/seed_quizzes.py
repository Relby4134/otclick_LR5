from django.core.management.base import BaseCommand
from django.db import transaction

from surveys.models import Choice, Question, Survey


QUIZZES = [
    ('Основы Python', 'Пять вопросов о Python. В вопросах с несколькими ответами выберите все правильные варианты.', [
        ('Какой результат вернёт выражение 2 ** 3?', 'single', [('6', False), ('8', True), ('9', False), ('5', False)]),
        ('Какие из перечисленных типов данных изменяемые?', 'multiple', [('list — список', True), ('dict — словарь', True), ('tuple — кортеж', False), ('str — строка', False)]),
        ('Какая функция возвращает количество элементов списка?', 'single', [('size()', False), ('count()', False), ('len()', True), ('length()', False)]),
        ('Что обозначает значение None?', 'single', [('Отсутствие значения', True), ('Число ноль', False), ('Пустую строку', False), ('Логическое значение True', False)]),
        ('Какие конструкции используются для циклов в Python?', 'multiple', [('for', True), ('while', True), ('if', False), ('def', False)]),
    ]),
    ('Основы веб-разработки', 'Проверьте знания HTML, CSS, HTTP и Django. Пять вопросов с автоматической проверкой.', [
        ('Для чего используется HTML?', 'single', [('Для структуры содержимого страницы', True), ('Только для хранения данных', False), ('Для настройки сервера', False)]),
        ('Какие задачи обычно решает CSS?', 'multiple', [('Цвета и шрифты', True), ('Расположение элементов', True), ('Проверка пароля на сервере', False), ('Запросы к базе данных', False)]),
        ('Что означает HTTP-статус 404?', 'single', [('Запрос выполнен успешно', False), ('Ресурс не найден', True), ('Внутренняя ошибка сервера', False)]),
        ('Какие задачи Django выполняет на сервере?', 'multiple', [('Обработка HTTP-запросов', True), ('Работа с базой данных через ORM', True), ('Отрисовка пикселей в браузере', False), ('Применение CSS в браузере', False)]),
        ('Какой HTML-элемент создаёт ползунок?', 'single', [('<input type="range">', True), ('<input type="text">', False), ('<textarea>', False), ('<select>', False)]),
    ]),
]


class Command(BaseCommand):
    help = 'Добавить два демонстрационных теста с правильными ответами, без дубликатов'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        for title, description, questions in QUIZZES:
            survey, created = Survey.objects.get_or_create(
                title=title, defaults={'description': description, 'is_quiz': True, 'is_active': True},
            )
            if not created:
                self.stdout.write(f'Уже существует: {title}')
                continue
            for order, (text, kind, choices) in enumerate(questions, start=1):
                question = Question.objects.create(survey=survey, title=text, kind=kind, order=order)
                Choice.objects.bulk_create([
                    Choice(question=question, label=label, is_correct=correct)
                    for label, correct in choices
                ])
            self.stdout.write(self.style.SUCCESS(f'Создан тест: {title}'))
