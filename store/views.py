import json
import smtplib
from email.mime.text import MIMEText

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .models import Product, Size, Order, OrderItem


# ── Utilidad: carrito en sesión ────────────────────────────────────────────

def _get_cart(request):
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


# ── Vista principal: catálogo con filtros ───────────────────────────────────

def catalog(request):
    products = Product.objects.filter(is_active=True).prefetch_related('sizes')

    gender    = request.GET.get('gender', '')
    style     = request.GET.get('style', '')
    size_name = request.GET.get('size', '')

    if gender:
        products = products.filter(gender=gender)
    if style:
        products = products.filter(style=style)
    if size_name:
        products = products.filter(sizes__name=size_name)

    genders = Product.GENDER_CHOICES
    styles  = Product.STYLE_CHOICES
    sizes   = Size.objects.all()

    cart       = _get_cart(request)
    cart_count = sum(cart.values())

    context = {
        'products':      products,
        'genders':       genders,
        'styles':        styles,
        'sizes':         sizes,
        'active_gender': gender,
        'active_style':  style,
        'active_size':   size_name,
        'cart_count':    cart_count,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/product_grid.html', context)

    return render(request, 'index.html', context)


# ── Detalle de producto ─────────────────────────────────────────────────────

def product_detail(request, slug):
    product    = get_object_or_404(Product, slug=slug, is_active=True)
    cart       = _get_cart(request)
    cart_count = sum(cart.values())
    return render(request, 'product_detail.html', {
        'product':    product,
        'cart_count': cart_count,
    })


# ── API: añadir al carrito ───────────────────────────────────────────────────

@require_POST
def cart_add(request):
    data       = json.loads(request.body)
    product_id = str(data.get('product_id'))
    qty        = int(data.get('qty', 1))

    product = get_object_or_404(Product, id=product_id, is_active=True)

    cart = _get_cart(request)
    cart[product_id] = cart.get(product_id, 0) + qty
    _save_cart(request, cart)

    cart_count    = sum(cart.values())
    cart_subtotal = _calculate_subtotal(cart)

    return JsonResponse({
        'ok':            True,
        'cart_count':    cart_count,
        'cart_subtotal': str(cart_subtotal),
        'message':       f'"{product.name}" añadido al pedido.',
    })


@require_POST
def cart_remove(request):
    data       = json.loads(request.body)
    product_id = str(data.get('product_id'))

    cart = _get_cart(request)
    if product_id in cart:
        del cart[product_id]
    _save_cart(request, cart)

    cart_count    = sum(cart.values())
    cart_subtotal = _calculate_subtotal(cart)

    return JsonResponse({
        'ok':            True,
        'cart_count':    cart_count,
        'cart_subtotal': str(cart_subtotal),
    })


def cart_view(request):
    cart       = _get_cart(request)
    cart_items = []

    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=int(pid), is_active=True)
            cart_items.append({
                'product':  p,
                'qty':      qty,
                'subtotal': p.price * qty,
            })
        except Product.DoesNotExist:
            pass

    total      = sum(item['subtotal'] for item in cart_items)
    cart_count = sum(cart.values())

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total':      total,
        'cart_count': cart_count,
    })


def _calculate_subtotal(cart):
    total = 0
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=int(pid))
            total += p.price * qty
        except Product.DoesNotExist:
            pass
    return round(total, 2)


# ── Confirmar pedido ────────────────────────────────────────────────────────

@login_required(login_url='/cuenta/login/')
@require_POST
def confirm_order(request):
    cart = _get_cart(request)
    if not cart:
        return JsonResponse({'ok': False, 'error': 'Tu carrito está vacío.'})

    errors     = []
    items_info = []
    total      = 0

    # Validar stock
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=int(pid))
            if p.stock < qty:
                errors.append(f'Stock insuficiente para "{p.name}" (disponible: {p.stock}).')
        except Product.DoesNotExist:
            errors.append(f'Producto ID {pid} no encontrado.')

    if errors:
        return JsonResponse({'ok': False, 'error': ' '.join(errors)})

    # Crear pedido
    order = Order.objects.create(user=request.user, total=0)

    for pid, qty in cart.items():
        p        = Product.objects.get(id=int(pid))
        subtotal = p.price * qty

        OrderItem.objects.create(
            order=order, product=p, quantity=qty,
            unit_price=p.price, subtotal=subtotal,
        )

        p.stock -= qty
        p.save(update_fields=['stock'])

        items_info.append(f'- {p.name} x{qty} — ${subtotal}')
        total += subtotal

    order.total = total
    order.save(update_fields=['total'])

    # Vaciar carrito
    _save_cart(request, {})

    # Enviar correo al admin
    _enviar_correo_pedido(order, items_info, request.user)

    return JsonResponse({
        'ok':    True,
        'code':  order.code,
        'total': str(order.total),
    })


def _enviar_correo_pedido(order, items_info, user):
    try:
        cuerpo = (
            f"Nuevo pedido recibido en Brana 🌸\n\n"
            f"Codigo de pedido: #{order.code}\n"
            f"Cliente: {user.email}\n"
            f"Fecha: {order.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"Productos:\n" + "\n".join(items_info) + "\n\n"
            f"TOTAL: ${order.total}\n\n"
            f"El cliente debe presentar el codigo #{order.code} al recoger su pedido."
        )

        msg            = MIMEText(cuerpo, 'plain')
        msg['From']    = settings.EMAIL_HOST_USER
        msg['To']      = settings.ADMIN_EMAIL
        msg['Subject'] = f'Nuevo Pedido Brana — Codigo #{order.code}'

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, settings.ADMIN_EMAIL, msg.as_string())
    except Exception as e:
        print(f'Error enviando correo: {e}')