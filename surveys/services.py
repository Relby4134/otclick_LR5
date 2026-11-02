from .models import Answer
from django.db.models import F
import re
import unicodedata


def normalize_text(value):
    text = unicodedata.normalize('NFKC', str(value)).casefold().replace('ё', 'е')
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def public_summary(survey):
    if not survey.is_quiz:
        return {'is_quiz': False, 'total': survey.responses.count()}
    evaluated = survey.responses.filter(score__isnull=False, graded_count__gt=0)
    total = evaluated.count()
    passed = evaluated.annotate(earned=F('score') * 100,
        required=F('graded_count') * survey.pass_percent).filter(earned__gte=F('required')).count()
    return {'is_quiz': True, 'total': total, 'pass_percent': survey.pass_percent,
            'success_percent': round(passed / total * 100) if total else None}


def build_answer(response, question, value):
    choices = list(question.choices.all())
    selected = set(value if isinstance(value, list) else [str(value)])
    correct = {str(c.pk) for c in choices if c.is_correct}
    verdict = None
    correct_value = ''
    if response.survey.is_quiz and question.kind in ('single', 'multiple', 'image') and correct:
        verdict = selected == correct
        correct_value = ', '.join(c.label for c in choices if c.is_correct)
    elif response.survey.is_quiz and question.kind == 'puzzle':
        verdict = value is not None and abs(value - question.puzzle_target) <= question.puzzle_tolerance
        correct_value = f'Положение {question.puzzle_target} из 100, погрешность ±{question.puzzle_tolerance}'
    elif response.survey.is_quiz and question.kind == 'slider' and question.correct_number is not None:
        verdict = value == question.correct_number
        correct_value = str(question.correct_number)
    elif response.survey.is_quiz and question.kind in ('text', 'audio') and question.correct_text.strip():
        accepted = [line.strip() for line in question.correct_text.splitlines() if line.strip()]
        verdict = normalize_text(value or '') in {normalize_text(line) for line in accepted}
        correct_value = ' / '.join(accepted)
    if question.kind in ('single', 'multiple', 'image'):
        display = ', '.join(c.label for c in choices if str(c.pk) in selected) or 'Без ответа'
    elif question.kind == 'puzzle':
        display = f'Положение {value} из 100' if value is not None else 'Без ответа'
    else:
        display = str(value) if value is not None and value != '' else 'Без ответа'
    return Answer(response=response, question=question, value=value if value is not None else '',
                  question_title=question.title, display_value=display, is_correct=verdict,
                  correct_value=correct_value, explanation=question.explanation)
