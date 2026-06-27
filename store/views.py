# store/views.py
import json
from django.shortcuts      import render, get_object_or_404
from django.http           import JsonResponse
from django.views.decorators.http import require_POST
from .models import Product, Size


# ─── Utilidad: carrito en sesión ────────────────────────────────────────────

def _get_cart(request):
    """Devuelve el carrito guardado en la sesión como dict {product_id: qty}."""
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


# ─── Vista principal: catálogo con filtros ───────────────────────────────────

def catalog(request):
    products = Product.objects.filter(is_active=True).prefetch_related('sizes')

    # Filtros GET
    gender     = request.GET.get('gender', '')
    style      = request.GET.get('style', '')
    size_name  = request.GET.get('size', '')

    if gender:
        products = products.filter(gender=gender)
    if style:
        products = products.filter(style=style)
    if size_name:
        products = products.filter(sizes__name=size_name)

    # Opciones de filtro disponibles
    genders = Product.GENDER_CHOICES
    styles  = Product.STYLE_CHOICES
    sizes   = Size.objects.all()

    # Carrito para el navbar
    cart       = _get_cart(request)
    cart_count = sum(cart.values())

    context = {
        'products':    products,
        'genders':     genders,
        'styles':      styles,
        'sizes':       sizes,
        'active_gender': gender,
        'active_style':  style,
        'active_size':   size_name,
        'cart_count':    cart_count,
    }

    # Si la petición viene de HTMX, devuelve sólo el grid parcial
    if request.headers.get('HX-Request'):
        return render(request, 'partials/product_grid.html', context)

    return render(request, 'index.html', context)


# ─── Detalle de producto ─────────────────────────────────────────────────────

def product_detail(request, slug):
    product    = get_object_or_404(Product, slug=slug, is_active=True)
    cart       = _get_cart(request)
    cart_count = sum(cart.values())
    return render(request, 'product_detail.html', {
        'product':    product,
        'cart_count': cart_count,
    })


# ─── API: añadir al carrito (AJAX/HTMX) ─────────────────────────────────────

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
        'ok':        True,
        'cart_count':    cart_count,
        'cart_subtotal': str(cart_subtotal),
        'message':   f'"{product.name}" añadido al carrito.',
    })


# ─── API: quitar del carrito ─────────────────────────────────────────────────

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


# ─── Vista: ver carrito ───────────────────────────────────────────────────────

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


# ─── Simulación de compra (resta stock) ──────────────────────────────────────

@require_POST
def simulate_purchase(request):
    cart = _get_cart(request)
    errors = []

    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=int(pid))
            if p.stock >= qty:
                p.stock -= qty
                p.save(update_fields=['stock'])
            else:
                errors.append(f'Stock insuficiente para "{p.name}" (disponible: {p.stock}).')
        except Product.DoesNotExist:
            errors.append(f'Producto ID {pid} no encontrado.')

    if not errors:
        _save_cart(request, {})   # vaciar carrito
        return JsonResponse({'ok': True, 'message': '¡Compra simulada con éxito! Stock actualizado.'})

    return JsonResponse({'ok': False, 'errors': errors}, status=400)


# ─── Helper privado ───────────────────────────────────────────────────────────

def _calculate_subtotal(cart):
    total = 0
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=int(pid))
            total += p.price * qty
        except Product.DoesNotExist:
            pass
    return round(total, 2)