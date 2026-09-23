from django import template

register = template.Library()


@register.filter
def cart_qty(cart, product_id):
    return cart.get_quantity(product_id)