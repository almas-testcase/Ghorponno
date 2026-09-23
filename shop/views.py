import random
import string
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Category, Product, Order, OrderItem,  PromoCode, Advertisement, DeliverySettings
from .cart import Cart
from pages.models import Review
from django.http import JsonResponse
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db.models import Q
from django.utils import timezone


def _safe_int(value, default=1, minimum=1, maximum=999):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(n, maximum))


def home(request):
    cart = Cart(request)
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True, is_best_selling=True)[:5]
    reviews = Review.objects.filter(is_approved=True).order_by('-created_at')[:10]
    ads = Advertisement.objects.filter(is_active=True)

    flash_qs = Product.objects.filter(
        is_active=True, is_flash_sale=True, flash_sale_end__gt=timezone.now()
    ).order_by('flash_sale_end')
    flash_sale_products = flash_qs[:8]
    flash_sale_end = flash_qs.first().flash_sale_end if flash_qs.exists() else None

    category_products = []
    for cat in categories:
        cat_products = Product.objects.filter(category=cat, is_active=True)[:6]
        if cat_products:
            category_products.append({'category': cat, 'products': cat_products})

    context = {
        'categories': categories,
        'products': products,
        'cart': cart,
        'category_products': category_products,
        'reviews': reviews,
        'flash_sale_products': flash_sale_products,
        'flash_sale_end': flash_sale_end,
        'ads': ads,
    }
    return render(request, 'home.html', context)


from django.core.paginator import Paginator

def category_detail(request, slug):
    cart = Cart(request)
    category = get_object_or_404(Category, slug=slug)
    product_qs = Product.objects.filter(category=category, is_active=True)

    paginator = Paginator(product_qs, 24)  # 24 per page
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
        'cart': cart,
    }
    return render(request, 'shop/category.html', context)

def product_detail(request, slug):
    cart = Cart(request)
    product = get_object_or_404(Product, slug=slug, is_active=True)
    context = {
        'product': product,
        'cart': cart,
    }
    return render(request, 'shop/product_detail.html', context)



@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = _safe_int(request.POST.get('quantity', 1))

    current_qty = cart.get_quantity(product.id)
    if current_qty + quantity > product.stock:
        if _is_ajax(request):
            return JsonResponse({'error': f'Only {product.stock} in stock.'}, status=400)
        return redirect('shop:cart_detail')

    cart.add(product=product, quantity=quantity)

    if _is_ajax(request):
        return JsonResponse({
            'quantity': cart.get_quantity(product.id),
            'cart_count': len(cart),
            'cart_total': str(cart.get_total_price()),
        })
    return redirect('shop:cart_detail')



@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)

    if _is_ajax(request):
        return JsonResponse({
            'quantity': 0,
            'cart_count': len(cart),
            'cart_total': str(cart.get_total_price()),
        })
    return redirect('shop:cart_detail')



@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = _safe_int(request.POST.get('quantity', 1))

    if quantity > 0:
        cart.add(product=product, quantity=quantity, update_quantity=True)
    else:
        cart.remove(product)

    if _is_ajax(request):
        return JsonResponse({
            'quantity': cart.get_quantity(product.id),
            'cart_count': len(cart),
            'cart_total': str(cart.get_total_price()),
        })
    return redirect('shop:cart_detail')



def cart_detail(request):
    cart = Cart(request)
    return render(request, 'shop/cart.html', {'cart': cart})


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(search_keywords__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True
        ).distinct()[:6]
        for p in products:
            price = p.discount_price if p.discount_price else p.price
            results.append({
                'name': p.name,
                'price': str(price),
                'url': f'/product/{p.slug}/',
                'image': p.image.url if p.image else '',
            })
    return JsonResponse({'results': results})



def generate_order_id():
    date_part = timezone.now().strftime('%y%m%d')
    last_order = Order.objects.filter(
        order_id__startswith=f'BA-{date_part}-'
    ).order_by('-id').first()

    if last_order:
        last_seq = int(last_order.order_id.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f'BA-{date_part}-{next_seq:04d}'



def get_delivery_charges():
    s = DeliverySettings.load()
    return {'dhaka': s.dhaka_charge, 'outside': s.outside_charge}


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('shop:cart_detail')

    delivery_charges = get_delivery_charges()
    delivery_settings = DeliverySettings.load()

    subtotal = cart.get_total_price()
    promo_code = request.session.get('promo_code', '')
    discount_amount = Decimal(request.session.get('promo_discount', '0'))
    delivery_area = request.session.get('delivery_area', 'dhaka')
    if delivery_area not in delivery_charges:
        delivery_area = 'dhaka'
    delivery_charge = delivery_charges[delivery_area]
    final_total = subtotal - discount_amount + delivery_charge

    if request.method == 'POST':
        delivery_area = request.POST.get('delivery_area', delivery_area)
        if delivery_area not in delivery_charges:
            delivery_area = 'dhaka'
        delivery_charge = delivery_charges[delivery_area]
        final_total = subtotal - discount_amount + delivery_charge
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        order_id = generate_order_id()
        while Order.objects.filter(order_id=order_id).exists():
            order_id = generate_order_id()

        order = Order.objects.create(
            order_id=order_id,
            full_name=full_name,
            phone=phone,
            address=address,
            subtotal=subtotal,
            promo_code=promo_code,
            discount_amount=discount_amount,
            delivery_area=delivery_area,
            delivery_charge=delivery_charge,
            total_amount=final_total,
        )

        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['price'],
            )
            # reduce stock
            if item['product']:
                item['product'].stock = max(0, item['product'].stock - item['quantity'])
                item['product'].save(update_fields=['stock'])


        area_label = 'Inside Dhaka' if delivery_area == 'dhaka' else 'Outside Dhaka'


        # Build order items HTML
        order_items_html = ""

        for item in cart:
            order_items_html += f"""
                <tr>
                    <td style="
                        padding:14px 12px;
                        border-bottom:1px solid #eeeeee;
                        color:#333333;
                        font-size:14px;
                    ">
                        <strong>{item['product'].name}</strong>
                    </td>

                    <td style="
                        padding:14px 12px;
                        border-bottom:1px solid #eeeeee;
                        text-align:center;
                        color:#555555;
                        font-size:14px;
                    ">
                        {item['quantity']}
                    </td>

                    <td style="
                        padding:14px 12px;
                        border-bottom:1px solid #eeeeee;
                        text-align:right;
                        color:#333333;
                        font-size:14px;
                        font-weight:600;
                    ">
                        ৳{item['total_price']}
                    </td>
                </tr>
            """

        # Plain-text fallback
        order_items_text = ""

        for item in cart:
            order_items_text += (
                f"- {item['product'].name} × {item['quantity']} "
                f"= ৳{item['total_price']}\n"
            )

        email_text = f"""
New Order Received - Ghorponyo

Order ID: {order.order_id}

Customer Information
Name: {full_name}
Phone: {phone}
Address: {address}
Delivery Area: {area_label}

Order Items:
{order_items_text}

Subtotal: ৳{subtotal}
Discount: ৳{discount_amount}
Delivery Charge: ৳{delivery_charge}
Total: ৳{final_total}

Please process this order as soon as possible.

Ghorponyo
Your Trusted Online Shop
"""

        # Beautiful HTML email
        email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Order - Ghorponyo</title>
</head>

<body style="
    margin:0;
    padding:0;
    background:#f4f7f6;
    font-family:Arial, Helvetica, sans-serif;
    color:#333333;
">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#f4f7f6;padding:30px 15px;">

<tr>
<td align="center">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="
           max-width:650px;
           background:#ffffff;
           border-radius:14px;
           overflow:hidden;
           border:1px solid #e5e5e5;
       ">

    <!-- HEADER -->
    <tr>
        <td style="
            background:#198754;
            padding:28px 25px;
            text-align:center;
        ">
            <div style="
                font-size:28px;
                font-weight:700;
                color:#ffffff;
                margin-bottom:6px;
            ">
                Ghorponyo
            </div>

            <div style="
                font-size:14px;
                color:#eafff2;
            ">
                Your Trusted Online Shop
            </div>
        </td>
    </tr>

    <!-- ORDER RECEIVED -->
    <tr>
        <td style="padding:30px 30px 15px;">

            <div style="
                background:#eaf8f0;
                border:1px solid #ccebd8;
                border-radius:10px;
                padding:18px;
                text-align:center;
            ">

                <div style="
                    font-size:23px;
                    font-weight:700;
                    color:#198754;
                    margin-bottom:6px;
                ">
                    🛍️ New Order Received
                </div>

                <div style="
                    font-size:14px;
                    color:#666666;
                ">
                    A new order has been placed on Ghorponyo.
                </div>

            </div>

        </td>
    </tr>

    <!-- ORDER ID -->
    <tr>
        <td style="padding:10px 30px 20px;">

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="
                       background:#fafafa;
                       border:1px solid #eeeeee;
                       border-radius:10px;
                   ">

                <tr>
                    <td style="
                        padding:14px 16px;
                        font-size:13px;
                        color:#777777;
                    ">
                        ORDER ID
                    </td>

                    <td style="
                        padding:14px 16px;
                        text-align:right;
                        font-size:15px;
                        font-weight:700;
                        color:#198754;
                    ">
                        #{order.order_id}
                    </td>
                </tr>

            </table>

        </td>
    </tr>

    <!-- CUSTOMER -->
    <tr>
        <td style="padding:0 30px 20px;">

            <h3 style="
                margin:0 0 12px;
                font-size:17px;
                color:#222222;
            ">
                👤 Customer Information
            </h3>

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="
                       border:1px solid #eeeeee;
                       border-radius:10px;
                       overflow:hidden;
                   ">

                <tr>
                    <td style="
                        padding:12px 15px;
                        width:120px;
                        background:#fafafa;
                        font-size:13px;
                        color:#777777;
                    ">
                        Name
                    </td>

                    <td style="
                        padding:12px 15px;
                        font-size:14px;
                        font-weight:600;
                    ">
                        {full_name}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:12px 15px;
                        background:#fafafa;
                        font-size:13px;
                        color:#777777;
                    ">
                        Phone
                    </td>

                    <td style="
                        padding:12px 15px;
                        font-size:14px;
                        font-weight:600;
                    ">
                        {phone}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:12px 15px;
                        background:#fafafa;
                        font-size:13px;
                        color:#777777;
                    ">
                        Address
                    </td>

                    <td style="
                        padding:12px 15px;
                        font-size:14px;
                        line-height:1.5;
                    ">
                        {address}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:12px 15px;
                        background:#fafafa;
                        font-size:13px;
                        color:#777777;
                    ">
                        Delivery
                    </td>

                    <td style="
                        padding:12px 15px;
                        font-size:14px;
                        font-weight:600;
                    ">
                        {area_label}
                    </td>
                </tr>

            </table>

        </td>
    </tr>

    <!-- PRODUCTS -->
    <tr>
        <td style="padding:0 30px 20px;">

            <h3 style="
                margin:0 0 12px;
                font-size:17px;
                color:#222222;
            ">
                🛒 Order Items
            </h3>

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="
                       border:1px solid #eeeeee;
                       border-radius:10px;
                       overflow:hidden;
                   ">

                <tr style="background:#f8faf9;">

                    <th style="
                        padding:12px;
                        text-align:left;
                        font-size:12px;
                        color:#777777;
                    ">
                        PRODUCT
                    </th>

                    <th style="
                        padding:12px;
                        text-align:center;
                        font-size:12px;
                        color:#777777;
                    ">
                        QTY
                    </th>

                    <th style="
                        padding:12px;
                        text-align:right;
                        font-size:12px;
                        color:#777777;
                    ">
                        PRICE
                    </th>

                </tr>

                {order_items_html}

            </table>

        </td>
    </tr>

    <!-- SUMMARY -->
    <tr>
        <td style="padding:0 30px 25px;">

            <h3 style="
                margin:0 0 12px;
                font-size:17px;
                color:#222222;
            ">
                💰 Order Summary
            </h3>

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="
                       background:#fafafa;
                       border:1px solid #eeeeee;
                       border-radius:10px;
                   ">

                <tr>
                    <td style="padding:10px 15px;color:#666666;font-size:14px;">
                        Subtotal
                    </td>

                    <td style="
                        padding:10px 15px;
                        text-align:right;
                        font-size:14px;
                    ">
                        ৳{subtotal}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px 15px;color:#666666;font-size:14px;">
                        Discount
                    </td>

                    <td style="
                        padding:10px 15px;
                        text-align:right;
                        font-size:14px;
                        color:#dc3545;
                    ">
                        - ৳{discount_amount}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px 15px;color:#666666;font-size:14px;">
                        Delivery Charge
                    </td>

                    <td style="
                        padding:10px 15px;
                        text-align:right;
                        font-size:14px;
                    ">
                        ৳{delivery_charge}
                    </td>
                </tr>

                <tr>
                    <td colspan="2" style="padding:0 15px;">
                        <div style="height:1px;background:#dddddd;"></div>
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:16px 15px;
                        font-size:17px;
                        font-weight:700;
                    ">
                        TOTAL
                    </td>

                    <td style="
                        padding:16px 15px;
                        text-align:right;
                        font-size:21px;
                        font-weight:700;
                        color:#198754;
                    ">
                        ৳{final_total}
                    </td>
                </tr>

            </table>

        </td>
    </tr>

    <!-- ACTION -->
    <tr>
        <td style="padding:0 30px 30px;">

            <div style="
                background:#fff8e6;
                border-left:4px solid #f0ad4e;
                border-radius:6px;
                padding:14px 16px;
                font-size:13px;
                color:#665522;
                line-height:1.6;
            ">
                <strong>⚠️ Action Required</strong><br>
                Please review and process this order as soon as possible.
            </div>

        </td>
    </tr>

    <!-- FOOTER -->
    <tr>
        <td style="
            background:#f8f9fa;
            border-top:1px solid #eeeeee;
            padding:22px 30px;
            text-align:center;
        ">

            <div style="
                font-size:15px;
                font-weight:700;
                color:#198754;
                margin-bottom:5px;
            ">
                Ghorponyo
            </div>

            <div style="
                font-size:12px;
                color:#888888;
                line-height:1.6;
            ">
                Quality Products at Affordable Prices<br>
                Your Trusted Online Shop
            </div>

        </td>
    </tr>

</table>

</td>
</tr>

</table>

</body>
</html>
"""

        try:
            email = EmailMultiAlternatives(
                subject=f'🛍️ New Order #{order.order_id} - Ghorponyo',
                body=email_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.ADMIN_EMAIL],
            )

            email.attach_alternative(email_html, "text/html")
            email.send(fail_silently=False)

        except Exception as e:
            print("EMAIL ERROR:", e)

        # Send confirmation to the customer, if they gave an email
        customer_email = request.POST.get('email', '').strip()
        if customer_email:
            order.email = customer_email
            order.save(update_fields=['email'])
            try:
                cust_mail = EmailMultiAlternatives(
                    subject=f'Your Ghorponyo Order #{order.order_id} is confirmed',
                    body=f"Hi {full_name},\n\nThanks for your order! Order ID: {order.order_id}\nTotal: ৳{final_total}\n\nWe'll contact you shortly to confirm delivery.\n\nGhorponyo",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[customer_email],
                )
                cust_mail.attach_alternative(email_html, "text/html")
                cust_mail.send(fail_silently=True)
            except Exception as e:
                print("CUSTOMER EMAIL ERROR:", e)

        cart.clear()
        request.session.pop('promo_code', None)
        request.session.pop('promo_discount', None)
        request.session.pop('delivery_area', None)

        return redirect('shop:order_success', order_id=order.order_id)

    context = {
        'cart': cart,
        'subtotal': subtotal,
        'promo_code': promo_code,
        'discount_amount': discount_amount,
        'delivery_area': delivery_area,
        'delivery_charge': delivery_charge,
        'final_total': final_total,
        'delivery_settings': delivery_settings, 
    }
    return render(request, 'shop/checkout.html', context)


@require_POST
def set_delivery_area(request):
    delivery_charges = get_delivery_charges()
    area = request.POST.get('delivery_area', 'dhaka')
    if area not in delivery_charges:
        area = 'dhaka'
    request.session['delivery_area'] = area

    cart = Cart(request)
    subtotal = cart.get_total_price()
    discount_amount = Decimal(request.session.get('promo_discount', '0'))
    delivery_charge = delivery_charges[area]
    final_total = subtotal - discount_amount + delivery_charge

    return JsonResponse({
        'success': True,
        'delivery_charge': str(delivery_charge),
        'new_total': str(final_total),
    })




def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'shop/order_success.html', {'order': order})



def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'



def apply_promo(request):
    if request.method == 'POST':
        code = request.POST.get('promo_code', '').strip().upper()
        cart = Cart(request)

        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
        except PromoCode.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid or expired promo code.'})

        from django.utils import timezone
        if promo.valid_till and promo.valid_till < timezone.now().date():
            return JsonResponse({'success': False, 'message': 'This promo code has expired.'})

        subtotal = cart.get_total_price()
        discount = (subtotal * promo.discount_percent) / 100
        if promo.max_discount_amount and discount > promo.max_discount_amount:
            discount = promo.max_discount_amount

        request.session['promo_code'] = promo.code
        request.session['promo_discount'] = str(discount)

        return JsonResponse({
            'success': True,
            'message': f'Promo applied! {promo.discount_percent}% off.',
            'discount': str(discount),
            'new_total': str(subtotal - discount),
        })

    return JsonResponse({'success': False, 'message': 'Invalid request.'})


def remove_promo(request):
    request.session.pop('promo_code', None)
    request.session.pop('promo_discount', None)
    return JsonResponse({'success': True})



def track_order(request):
    phone = request.GET.get('phone', '').strip()
    orders = None
    searched = False

    if phone:
        searched = True
        orders = Order.objects.filter(phone=phone).order_by('-created_at')

    context = {
        'phone': phone,
        'orders': orders,
        'searched': searched,
    }
    return render(request, 'shop/track_order.html', context)



@require_POST
def buy_now(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=1)
    return redirect('shop:checkout')


def combo_offers(request):
    cart = Cart(request)
    products = Product.objects.filter(is_active=True, is_combo_offer=True)
    context = {
        'products': products,
        'cart': cart,
    }
    return render(request, 'shop/combo_offers.html', context)