from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.shortcuts import render

from core.views.generic import UpdateView, CreateView
from core.views.mixins import SuperUserCheckMixin

import allauth.account.views as allauth_views
from allauth.account.views import ConfirmEmailView, LoginView
from allauth.account.utils import send_email_confirmation
from allauth.account.models import EmailAddress

from ..models import User
from .. import forms


class AccountRegister(CreateView):
    model = User
    form_class = forms.RegisterForm
    template_name = 'account/signup.html'
    success_url = reverse_lazy('account:verification')

    def form_valid(self, form):
        self.user = form.save(self.request)
        if self.user.email:
            send_email_confirmation(self.request, self.user)
        if self.user.phone:
            device = self.user.verificationdevice_set.create(
                unverified_phone=self.user.phone)
            device.generate_challenge()
            message = _("Verification Token sent to {phone}")
            message = message.format(phone=self.user.phone)
            messages.add_message(self.request, messages.SUCCESS, message)

        return super().form_valid(form)

    # def get_context_data(self, *args, **kwargs):
    #     context = super(AccountRegister, self).get_context_data(
    #         *args, **kwargs)
    #     context["user"] = self.request.user
    #     return context


class PasswordChangeView(LoginRequiredMixin,
                         SuperUserCheckMixin,
                         allauth_views.PasswordChangeView):
    success_url = reverse_lazy('account:profile')
    form_class = forms.ChangePasswordForm


class PasswordResetView(SuperUserCheckMixin,
                        allauth_views.PasswordResetView):
    form_class = forms.ResetPasswordForm


class PasswordResetFromKeyView(SuperUserCheckMixin,
                               allauth_views.PasswordResetFromKeyView):
    form_class = forms.ResetPasswordKeyForm


class AccountProfile(LoginRequiredMixin, UpdateView):
    model = User
    form_class = forms.ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('account:profile')

    def get_object(self, *args, **kwargs):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        emails_to_verify = EmailAddress.objects.filter(
            user=self.object, verified=False).exists()
        context['emails_to_verify'] = emails_to_verify
        return context

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['request'] = self.request
        return form_kwargs

    def form_valid(self, form):
        messages.add_message(self.request, messages.SUCCESS,
                             _("Successfully updated profile information"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR,
                             _("Failed to update profile information"))
        return super().form_invalid(form)


class AccountLogin(LoginView):
    def form_valid(self, form):
        user = form.user
        if not user.email_verified:
            user.is_active = False
            user.save()
            send_email_confirmation(self.request, user)

        return super().form_valid(form)


class ConfirmEmail(ConfirmEmailView):
    def post(self, *args, **kwargs):
        response = super().post(*args, **kwargs)

        user = self.get_object().email_address.user
        user.email = self.get_object().email_address.email
        user.email_verified = True
        user.is_active = True
        user.save()

        return response


class AccountVerificationView(FormView):
    template_name = 'accounts/account_verification.html'
    form_class = forms.TokenVerificationForm
    success_url = reverse_lazy('account:login')
