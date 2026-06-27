# store/admin.py
from django.contrib import admin
from .models import Product, Size


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ['name', 'gender', 'style', 'price', 'stock', 'is_active']
    list_filter   = ['gender', 'style', 'is_active', 'sizes']
    list_editable = ['price', 'stock', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal   = ('sizes',)