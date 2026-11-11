"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from test_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("run/", views.run_algorithm, name="run"),
    path("run/<uuid:run_id>/", views.get_run, name="run-status"),
    path("run/<uuid:run_id>/cancel/", views.cancel_run, name="cancel-run"),

]
