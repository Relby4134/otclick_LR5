from django.core.management.base import BaseCommand
from surveys.models import Survey, Question, Choice
class Command(BaseCommand):
    help = 'Создать демонстрационный опрос (без дубликатов)'
    def handle(self,*args,**kwargs):
        survey, created = Survey.objects.get_or_create(title='Ваш идеальный выходной',defaults={'description':'Небольшой опрос о том, что помогает вам перезагрузиться.'})
        if not created:
            self.stdout.write('Демонстрационный опрос уже существует.'); return
        q = Question.objects.create(survey=survey,title='Где вы хотели бы оказаться?',kind='image',order=1)
        for label, name in [('В горах','mountains'),('У моря','sea'),('В городе','city')]:
            Choice.objects.create(question=q,label=label,image_url=f'/static/surveys/{name}.svg')
        Question.objects.create(survey=survey,title='Насколько активным будет ваш отдых?',kind='slider',order=2,minimum=0,maximum=10)
        q = Question.objects.create(survey=survey,title='С кем вы проведёте этот день?',kind='single',order=3)
        for label in ['С друзьями','С семьёй','Наедине с собой']: Choice.objects.create(question=q,label=label)
        q = Question.objects.create(survey=survey,title='Что возьмёте с собой?',kind='multiple',order=4)
        for label in ['Книгу','Камеру','Наушники','Перекус']: Choice.objects.create(question=q,label=label)
        Question.objects.create(survey=survey,title='Опишите свой идеальный день',kind='text',order=5,required=False)
        self.stdout.write(self.style.SUCCESS('Демонстрационный опрос создан.'))
