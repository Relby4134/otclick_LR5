from django import forms

class SurveyForm(forms.Form):
    def __init__(self, *args, questions, **kwargs):
        super().__init__(*args, **kwargs)
        for q in questions:
            opts = dict(label=q.title, required=q.required)
            if q.kind in ('text', 'audio'):
                field = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={'rows':3}), **opts)
            elif q.kind == 'puzzle':
                field = forms.IntegerField(min_value=0, max_value=100,
                    initial=0 if q.puzzle_target >= 50 else 100,
                    widget=forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100, 'step': 1,
                        'aria-label': 'Положение фрагмента по горизонтали'}), **opts)
            elif q.kind == 'slider':
                field = forms.IntegerField(min_value=q.minimum, max_value=q.maximum, initial=q.minimum, widget=forms.NumberInput(attrs={'type':'range','min':q.minimum,'max':q.maximum}), **opts)
            else:
                choices = [(str(c.pk),c.label) for c in q.choices.all()]
                field = forms.MultipleChoiceField(choices=choices, widget=forms.CheckboxSelectMultiple, **opts) if q.kind == 'multiple' else forms.ChoiceField(choices=choices, widget=forms.RadioSelect, **opts)
            self.fields[f'q_{q.pk}'] = field
