from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy

from typing import Dict

from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

import shopping.models


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'accounts/signup.html'


class LoginRequiredTemplateView(generic.TemplateView, LoginRequiredMixin):
    pass


class ProfileEditView(LoginRequiredTemplateView):
    template_name = "accounts/updateUser.html"

    def get_context_data(self, **kwargs) -> Dict:
        context = super().get_context_data(**kwargs)
        context["prefectures"] = shopping.models.Prefecture.objects.all()

        return context



