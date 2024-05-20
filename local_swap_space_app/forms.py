from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, get_user_model, UserChangeForm
from django.core.validators import RegexValidator

from .models import Item, Category, ItemImage

# Retrieve the current active user model used in the project.
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating a new user.
    """
    city = forms.CharField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'city']


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form.
    """
    latitude = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        validators=[RegexValidator(r'^-?\d{1,2}\.\d+$', message="Invalid latitude format")]
    )
    longitude = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        validators=[RegexValidator(r'^-?\d{1,3}\.\d+$', message="Invalid longitude format")]
    )

    class Meta:
        model = User
        fields = ['username', 'password']


class CustomUserChangeForm(UserChangeForm):
    """
    Form for editing user profile information.
    """
    password = None  # Hide the password field in the form.

    class Meta:
        model = User
        fields = ['username', 'email', 'city']


class ItemForm(forms.ModelForm):
    """
    Form for creating and editing items.
    """

    class Meta:
        model = Item
        fields = ['name', 'description', 'category', 'status']

    def __init__(self, *args, **kwargs):
        """
        Custom initialization method to handle form initialization.
        """
        editable_name = kwargs.pop('editable_name', True)  # Determines whether the 'name' field should be editable.
        super(ItemForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()  # Sets queryset for category field.
        if not editable_name:
            self.fields['name'].disabled = True  # Disable 'name' field if it is not editable.


class RatingForm(forms.Form):
    """
    Form for rating items.
    """
    rating = forms.ChoiceField(choices=[(i, str(i)) for i in range(1, 6)],
                               widget=forms.RadioSelect)  # Rating options from 1 to 5.


class ItemImageForm(forms.ModelForm):
    """
    Form for adding item images.
    """

    class Meta:
        model = ItemImage
        fields = ['image']
