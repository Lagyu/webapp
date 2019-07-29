from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
# Create your views here.
from django.views.generic import TemplateView
from .models import Product, Category, SubProduct, Cart, ShoppingUser, ProductCart, ProductOrder, Warehouse, Order
from typing import List
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.urls import reverse, reverse_lazy

from django.forms import ModelForm

from django.core.exceptions import ObjectDoesNotExist

import datetime

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


class CartView(LoginRequiredMixin, generic.TemplateView):
    template_name = "shopping/templates/cart.html"


@login_required
def add_to_cart(request, product_id, sub_product_id):
    if request.method == 'GET':
        return product_detail(request, product_id, sub_product_id)

    if request.method == 'POST':

        context = get_product_detail_context(request, product_id, sub_product_id)

        sub_product_id = int(request.POST.get("sub_product_id"))
        sub_product = SubProduct.objects.get(id=sub_product_id)

        parent_user = request.user  # Type: ShoppingUser

        quantity_to_add = int(request.POST.get("quantity"))

        try:
            user_cart = Cart.objects.get(parent_user=parent_user)
        except ObjectDoesNotExist:
            user_cart = Cart.objects.create(parent_user=parent_user)

        try:
            product_cart = ProductCart.objects.get(parent_cart=user_cart, sub_product=sub_product)
            if product_cart.quantity + quantity_to_add <= sub_product.get_allocatable_stock_num():
                product_cart.quantity = product_cart.quantity + quantity_to_add
                product_cart.save()
            else:
                context["warning"] = "在庫数以上をカートに入れようとしたので、カートに入れた数を在庫数に修正しました。"

        except ObjectDoesNotExist:
            product_cart = ProductCart.objects.create(parent_cart=user_cart, sub_product=sub_product, quantity=quantity_to_add)

            setattr(product_cart, "quantity", quantity_to_add)

        context["added"] = product_cart

        return HttpResponseRedirect(reverse("shopping:added_to_cart",
                                            kwargs={"added_product_cart_id": product_cart.id}))


class RemoveFromCartConfirm(LoginRequiredMixin, generic.DeleteView):
    template_name = "shopping/templates/removeFromCartConfirm.html"

    model = ProductCart
    success_url = reverse_lazy("shopping:cart")


class PurchaseConfirm(LoginRequiredMixin, generic.TemplateView):
    template_name = "shopping/templates/purchaseConfirm.html"


@login_required
def cart_to_purchase_receiver(request):

    context = {}

    posted_dict = dict(request.POST)
    print(posted_dict)
    all_keys: List[str] = list(posted_dict.keys())

    checkbox_prefix_str = "purchase_check_"

    product_cart_ids_list = [int(key_str.replace(checkbox_prefix_str, "")) for key_str in all_keys
                             if checkbox_prefix_str in key_str]

    product_cart_query_set = ProductCart.objects.filter(id__in=product_cart_ids_list)

    context["product_carts"] = product_cart_query_set

    return render(request, "shopping/templates/purchaseConfirm.html", context)


@login_required
def commit_purchase_and_return_completed(request):
    posted_dict = dict(request.POST)
    print(posted_dict)
    all_keys: List[str] = list(posted_dict.keys())

    checkbox_prefix_str = "purchase_confirm_"

    product_cart_ids_list = [int(key_str.replace(checkbox_prefix_str, "")) for key_str in all_keys
                             if checkbox_prefix_str in key_str]

    order = Order.objects.create(parent_user=request.user, order_date=datetime.datetime.now(), is_shown=True)

    for product_cart_id in product_cart_ids_list:
        product_cart_obj = ProductCart.objects.get(id=product_cart_id)

        need_to_allocate_quantity = product_cart_obj.quantity

        stocks = list(product_cart_obj.get_available_stocks().order_by("-allocatable_num"))

        # もし在庫不足なら、戻す。
        if need_to_allocate_quantity > product_cart_obj.sub_product.get_allocatable_stock_num():
            return HttpResponseRedirect(reverse("shopping:purchase_failed", kwargs={"invalid_product_cart_id": product_cart_obj.id}))

        counter = 0
        while need_to_allocate_quantity > 0:
            if len(stocks) > 0:
                if stocks[counter].allocatable_num > need_to_allocate_quantity:
                    alloc_quantity = need_to_allocate_quantity
                    ProductOrder.objects.create(
                        parent_product=product_cart_obj.sub_product,
                        parent_order=order,
                        quantity=alloc_quantity,
                        warehouse=stocks[counter].warehouse
                    )
                    # 在庫を減らす
                    stocks[counter].allocatable_num -= alloc_quantity
                    stocks[counter].allocated_num += alloc_quantity
                    stocks[counter].save()

                    need_to_allocate_quantity -= alloc_quantity
                    counter += 1
                    break

                else:
                    alloc_quantity = stocks[counter].allocatable_num
                    ProductOrder.objects.create(
                        parent_product=product_cart_obj.sub_product,
                        parent_order=order,
                        quantity=alloc_quantity,
                        warehouse=stocks[counter].warehouse
                    )
                    # 在庫を減らす
                    stocks[counter].allocatable_num -= alloc_quantity
                    stocks[counter].allocated_num += alloc_quantity
                    stocks[counter].save()

                    need_to_allocate_quantity -= alloc_quantity
                    counter += 1

    return HttpResponseRedirect(reverse("shopping:purchase_complete", kwargs={"order_id": order.id}))











