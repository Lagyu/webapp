from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
# Create your views here.
from django.views.generic import TemplateView
from .models import Product, Category, SubProduct, Cart, ShoppingUser, ProductCart
from typing import List
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.urls import reverse

from django.forms import ModelForm

import operator
import functools
from django.db.models import Q, QuerySet
from django.views import generic

from typing import Dict

def index(request):
    context = {"user_id": request.user.id, "categories": Category.objects.all()}
    return render(request, "shopping/templates/main.html", context)


def get_category_from_category_id_or_return_none(category_id: str):
    try:
        cat_id_int = int(category_id)
    except ValueError:
        return None

    cat_obj = Category.objects.get(id=cat_id_int)
    return cat_obj


def convert_spaces_and_split_keywords(keywords: str) -> List[str]:
    replaced = keywords.replace("　", " ")
    return replaced.split(" ")


def search_products_with_keywords(keyword_list: List[str], category_obj=None) -> QuerySet:
    query = functools.reduce(operator.and_, (Q(name__contains=item) for item in keyword_list))
    if category_obj:
        result_products = Product.objects.filter(query, category=category_obj)
        return result_products
    else:
        result_products = Product.objects.filter(query)
        return result_products


def search_result(request):
    category_id = request.POST.get("category", "all")
    cat_obj = get_category_from_category_id_or_return_none(category_id)
    keywords_str = request.POST.get("keywords", "")
    keyword_list = convert_spaces_and_split_keywords(keywords_str)

    if cat_obj:
        result_products = search_products_with_keywords(keyword_list, cat_obj)

    else:
        result_products = search_products_with_keywords(keyword_list)

    context = {"user_id": request.user.id, "result_products": result_products, "keyword_list": keyword_list}
    return render(request, "shopping/templates/searchResult.html", context)


def get_product_detail_context(request, product_id: int, sub_product_id=0) -> Dict:
    product_to_show = Product.objects.get(id=product_id)
    sub_products = SubProduct.objects.filter(parent_product=product_to_show)

    if sub_product_id == 0:
        sub_product_to_show: SubProduct = sub_products.first()
    else:
        sub_product_to_show: SubProduct = sub_products.filter(id=sub_product_id).first()
        if sub_product_to_show is None:
            sub_product_to_show: SubProduct = sub_products.first()

    allocatable_stocks_sum = sub_product_to_show.get_allocatable_stock_num()

    context = {"product": product_to_show, "sub_products": sub_products, "sub_product_to_show": sub_product_to_show,
               "allocatable_stocks_sum": allocatable_stocks_sum}
    return context


def product_detail(request, product_id: int, sub_product_id=0):
    context = get_product_detail_context(request, product_id, sub_product_id)
    return render(request, "shopping/templates/itemDetail.html", context)


class CartView(generic.TemplateView, LoginRequiredMixin):
    template_name = "shopping/templates/cart.html"


def add_to_cart(request, product_id, sub_product_id):
    if request.method == 'GET':
        return product_detail(request, product_id, sub_product_id)

    if request.method == 'POST':

        context = get_product_detail_context(request, product_id, sub_product_id)

        sub_product_id = int(request.POST.get("sub_product_id"))
        sub_product = get_object_or_404(SubProduct, id=sub_product_id)

        parent_user = request.user  # Type: ShoppingUser

        quantity_to_add = int(request.POST.get("quantity"))

        product_cart, created_bool = ProductCart.objects.get_or_create(
            parent_cart=Cart.objects.get_or_create(parent_user=parent_user), sub_product=sub_product)

        if created_bool:
            setattr(product_cart, "quantity", quantity_to_add)
        else:
            if product_cart.quantity + quantity_to_add <= sub_product.get_allocatable_stock_num():
                setattr(product_cart, "quantity", product_cart.quantity + quantity_to_add)
            else:
                context["warning"] = "在庫数以上をカートに入れようとしたので、カートに入れた数を在庫数に修正しました。"

        context["added"] = product_cart

        HttpResponseRedirect(reverse("shopping:cart", args=()))




