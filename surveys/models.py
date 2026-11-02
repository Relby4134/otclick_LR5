from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

class Survey(models.Model):
    class Meta:
        verbose_name = 'опрос'
        verbose_name_plural = 'Опросы'
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Опубликован', default=True)
    is_quiz = models.BooleanField('Проверять правильность ответов', default=False)
    pass_percent = models.PositiveSmallIntegerField('Порог успешного прохождения, %', default=80,
        validators=[MinValueValidator(1), MaxValueValidator(100)])
    def __str__(self): return self.title

class Question(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField('Вопрос', max_length=300)
    kind = models.CharField('Тип', max_length=10, choices=[('text','Текст'),('single','Один вариант'),('multiple','Несколько вариантов'),('image','Картинки'),('slider','Ползунок'),('audio','Аудио с расшифровкой'),('puzzle','Пазл с ползунком')])
    required = models.BooleanField('Обязательный', default=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    minimum = models.IntegerField('Минимум', default=0)
    maximum = models.IntegerField('Максимум', default=10)
    correct_number = models.IntegerField('Правильное значение ползунка', null=True, blank=True)
    correct_text = models.TextField('Правильный текст', blank=True, help_text='Допустимые ответы — каждый с новой строки. Регистр, пунктуация и лишние пробелы не учитываются.')
    audio_url = models.CharField('Ссылка на аудиофайл', max_length=500, blank=True)
    explanation = models.TextField('Объяснение ответа', blank=True)
    puzzle_image = models.ImageField('Изображение для пазла', upload_to='puzzles/%Y/%m/', blank=True,
        help_text='Загрузите JPG, PNG или WebP. Фрагмент вырезается из этого изображения автоматически.')
    puzzle_target = models.PositiveSmallIntegerField('Положение фрагмента по горизонтали, %', default=65,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    puzzle_y = models.PositiveSmallIntegerField('Положение фрагмента по вертикали, %', default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    puzzle_tolerance = models.PositiveSmallIntegerField('Допустимая погрешность, пунктов', default=3,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text='Например: цель 65 и погрешность 3 — засчитываются положения от 62 до 68.')
    class Meta:
        ordering = ['order','pk']
        verbose_name = 'вопрос'
        verbose_name_plural = 'Вопросы'
    def __str__(self): return self.title
    def clean(self):
        if self.kind == 'slider' and self.minimum >= self.maximum:
            raise ValidationError('Максимум должен быть больше минимума.')
        if self.kind == 'slider' and self.correct_number is not None and not self.minimum <= self.correct_number <= self.maximum:
            raise ValidationError({'correct_number': 'Ответ должен находиться в диапазоне ползунка.'})
        if self.kind == 'audio' and not self.audio_url:
            raise ValidationError({'audio_url': 'Укажите аудиофайл.'})
        if self.kind == 'puzzle' and not self.puzzle_image:
            raise ValidationError({'puzzle_image': 'Загрузите изображение для пазла.'})

class Choice(models.Model):
    class Meta:
        verbose_name = 'вариант ответа'
        verbose_name_plural = 'Варианты ответа'
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    label = models.CharField('Подпись', max_length=200)
    image_url = models.URLField('Ссылка на картинку', blank=True)
    is_correct = models.BooleanField('Правильный вариант', default=False)
    def __str__(self): return self.label

class Response(models.Model):
    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'прохождение'
        verbose_name_plural = 'Пройденные опросы'
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    created_at = models.DateTimeField('Дата прохождения', auto_now_add=True)
    score = models.PositiveIntegerField('Правильных ответов', null=True, blank=True)
    graded_count = models.PositiveIntegerField('Проверенных вопросов', default=0)

    def __str__(self):
        return f'{self.survey} — прохождение №{self.pk}'

class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value = models.JSONField()
    question_title = models.CharField('Вопрос', max_length=300, blank=True)
    display_value = models.TextField('Ответ участника', blank=True)
    is_correct = models.BooleanField('Правильный ответ', null=True, blank=True)
    correct_value = models.TextField('Правильный ответ на момент прохождения', blank=True)
    explanation = models.TextField('Объяснение', blank=True)

    def readable_value(self):
        if self.display_value:
            return self.display_value
        if self.question.kind in ('single', 'multiple', 'image'):
            ids = self.value if isinstance(self.value, list) else [self.value]
            return ', '.join(self.question.choices.filter(pk__in=[int(v) for v in ids if str(v).isdigit()]).values_list('label', flat=True)) or 'Без ответа'
        return str(self.value) if self.value is not None and self.value != '' else 'Без ответа'
