from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import datetime  # for checking renewal date range.

from django import forms
# from catalog.cache import NameAgeBst


class RenewBookForm(forms.Form):
    """Form for a librarian to renew books."""
    renewal_date = forms.DateField(
        help_text="Enter a date between now and 4 weeks (default 3).")

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']

        # Check date is not in past.
        if data < datetime.date.today():
            raise ValidationError(_('Invalid date - renewal in past'))
        # Check date is in range librarian allowed to change (+4 weeks)
        if data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError(
                _('Invalid date - renewal more than 4 weeks ahead'))

        # Remember to always return the cleaned data.
        return data


class SignUpForm(forms.Form):
    """Form for a user to sign up."""
    name = forms.CharField(max_length=200, help_text="Sign Up Your Name (max 200 characters).")
    age = forms.IntegerField(max_value=120, min_value=18,
                             help_text="Enter your age between 18 (you must be at least 18) and 120 (are you alive?).")
    gpa = forms.DecimalField(max_digits=4, decimal_places=3,
                             help_text="Enter your GPA.")
    date = forms.DateTimeField(help_text="Enter your graduation date.")


class RemoveForm(forms.Form):
    """Form for a user to remove themselves from sign up."""
    name = forms.CharField(max_length=200, help_text="Enter Your Signed-Up Name (max 200 characters).")

    # def clean_name(self):
    #     data = self.cleaned_data['name']
    #
    #     # Check name is present.
    #     if not NameAgeBst.objects.find(data):
    #         raise ValidationError(_('You have not signed up yet!'))
    #
    #     return data
