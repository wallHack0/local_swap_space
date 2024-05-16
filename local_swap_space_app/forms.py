from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, get_user_model
from .models import Item, Category, ItemImage

# Retrieve the current active user model used in the project.
User = get_user_model()


# Form for creating a new user.
class CustomUserCreationForm(UserCreationForm):
    city = forms.CharField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'city']


# User authentication form.
class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']


# Form for creating and editing items.
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'description', 'category', 'status']

    def __init__(self, *args, **kwargs):
        editable_name = kwargs.pop('editable_name', True)  # Determines whether the 'name' field should be editable.
        super(ItemForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()  # Sets queryset for category field.
        if not editable_name:
            self.fields['name'].disabled = True  # Disable 'name' field if it is not editable.


# Form for rating items.
class RatingForm(forms.Form):
    rating = forms.ChoiceField(choices=[(i, str(i)) for i in range(1, 6)],
                               widget=forms.RadioSelect)  # Rating options from 1 to 5.


# Form for adding item images.
class ItemImageForm(forms.ModelForm):
    class Meta:
        model = ItemImage
        fields = ['image']
