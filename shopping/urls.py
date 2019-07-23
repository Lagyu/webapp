from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("search_result/", views.search_result, name="search_result"),
    path("cart/?remove=<int: product_cart_id>", views.CartView.as_view(), name="remove_from_cart_confirm"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("product/<int:product_id>/<int:sub_product_id>/add_to_cart", views.add_to_cart, name="add_to_cart"),
    path("product/<int:product_id>/<int:sub_product_id>/", views.product_detail, name="product_detail"),
]

