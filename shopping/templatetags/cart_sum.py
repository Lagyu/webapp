from django import template
from shopping.models import Cart, ProductCart
from functools import reduce
from operator import add

register = template.Library()


@register.filter
def cart_sum(cart: Cart):
    """
    Sum up all the cart content.
    Returns empty string on any error.
    """
    try:
        product_carts = cart.productcart_set.all()
    except AttributeError:
        product_carts = cart
    result = reduce(lambda a, b: a+b, [obj.get_sum() for obj in product_carts])

    return result


