from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, initial='daddy', widget = forms.TextInput(attrs = {'class': 'form-control'}))
    password = forms.CharField(max_length=30, initial='swiftdaddy', widget = forms.TextInput(attrs = {'class': 'form-control'}))
