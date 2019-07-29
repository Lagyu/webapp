from django.urls import path, re_path

from . import views

app_name = "shopping"

urlpatterns = [
    path('', views.index, name='index'),
    path("search_result/", views.search_result, name="search_result"),
    path("cart/remove/<int:pk>", views.RemoveFromCartConfirm.as_view(), name="remove_from_cart_confirm"),
    path("cart/added/<int:added_product_cart_id>", views.CartView.as_view(), name="added_to_cart"),
    path("cart/to_purchase", views.cart_to_purchase_receiver, name="cart_to_purchase_post_receiver"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("product/<int:product_id>/<int:sub_product_id>/add_to_cart", views.add_to_cart, name="add_to_cart"),
    path("product/<int:product_id>/<int:sub_product_id>/", views.product_detail, name="product_detail"),
    path("purchase/confirm", views.CartView.as_view, name="purchase_confirm"),  # todo: 仮
    path("purchase/failed/<int:invalid_product_cart_id>", views.CartView.as_view, name="purchase_failed"),  # todo: 仮
    path("purchase/complete/<int:order_id>", views.CartView.as_view, name="purchase_complete"),  # todo: 仮
]

