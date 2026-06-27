import json
import openpyxl
import smtplib
from io import BytesIO
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings

from .models import Product, Size, Sale


# ── Login / Logout ────────────────────────────────────────────────────────────

def panel_login(request):
    error = ''
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user and user.is_staff:
            login(request, user)
            return redirect('store:panel_inventario')
        error = 'Usuario o contraseña incorrectos.'
    return render(request, 'panel/login.html', {'error': error})


def panel_logout(request):
    logout(request)
    return redirect('store:panel_login')


# ── Inventario ────────────────────────────────────────────────────────────────

@login_required(login_url='/panel/login/')
def panel_inventario(request):
    products = Product.objects.prefetch_related('sizes').all()
    sizes    = Size.objects.all()
    return render(request, 'panel/inventario.html', {
        'products': products,
        'sizes':    sizes,
        'gender_choices': Product.GENDER_CHOICES,
        'style_choices':  Product.STYLE_CHOICES,
    })


@login_required(login_url='/panel/login/')
@require_POST
def panel_producto_crear(request):
    name   = request.POST.get('name', '').strip()
    gender = request.POST.get('gender')
    style  = request.POST.get('style')
    price  = request.POST.get('price')
    stock  = request.POST.get('stock', 0)
    desc   = request.POST.get('description', '')
    size_ids = request.POST.getlist('sizes')
    image  = request.FILES.get('image')

    p = Product(
        name=name, gender=gender, style=style,
        price=price, stock=stock, description=desc,
        is_active=True,
    )
    if image:
        p.image = image
    p.save()
    for sid in size_ids:
        try:
            p.sizes.add(Size.objects.get(id=sid))
        except Size.DoesNotExist:
            pass

    return JsonResponse({'ok': True, 'id': p.id, 'name': p.name})


@login_required(login_url='/panel/login/')
@require_POST
def panel_producto_editar(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.name   = request.POST.get('name', p.name).strip()
    p.gender = request.POST.get('gender', p.gender)
    p.style  = request.POST.get('style', p.style)
    p.price  = request.POST.get('price', p.price)
    p.stock  = request.POST.get('stock', p.stock)
    p.description = request.POST.get('description', p.description)
    p.is_active   = request.POST.get('is_active') == 'true'
    size_ids = request.POST.getlist('sizes')
    if request.FILES.get('image'):
        p.image = request.FILES['image']
    p.slug = ''   # forzar regeneración si cambia el nombre
    p.save()
    p.sizes.set(Size.objects.filter(id__in=size_ids))
    return JsonResponse({'ok': True})


@login_required(login_url='/panel/login/')
@require_POST
def panel_stock_ajustar(request, pk):
    p      = get_object_or_404(Product, pk=pk)
    delta  = int(request.POST.get('delta', 0))
    p.stock = max(0, p.stock + delta)
    p.save(update_fields=['stock'])
    return JsonResponse({'ok': True, 'stock': p.stock})


# ── Ventas ────────────────────────────────────────────────────────────────────

@login_required(login_url='/panel/login/')
def panel_ventas(request):
    today = timezone.now().date()
    sales = Sale.objects.filter(created_at__date=today).select_related('product', 'size')
    total_dia = sum(s.total for s in sales)
    return render(request, 'panel/ventas.html', {
        'sales':     sales,
        'total_dia': total_dia,
    })


@login_required(login_url='/panel/login/')
def panel_buscar_producto(request):
    q = request.GET.get('q', '').strip()
    try:
        if q.isdigit():
            p = Product.objects.get(id=int(q), is_active=True)
        else:
            p = Product.objects.get(name__iexact=q, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Producto no encontrado.'})

    sizes = [{'id': s.id, 'name': s.name} for s in p.sizes.all()]
    img   = p.image.url if p.image else ''
    return JsonResponse({
        'ok': True,
        'id': p.id, 'name': p.name,
        'price': str(p.price),
        'stock': p.stock,
        'image': img,
        'sizes': sizes,
    })


@login_required(login_url='/panel/login/')
@require_POST
def panel_registrar_venta(request):
    data = json.loads(request.body)
    items = data.get('items', [])
    if not items:
        return JsonResponse({'ok': False, 'error': 'Sin productos.'})

    ventas_creadas = []
    for item in items:
        p = get_object_or_404(Product, id=item['product_id'])
        qty  = int(item['qty'])
        size = None
        if item.get('size_id'):
            size = Size.objects.filter(id=item['size_id']).first()

        if p.stock < qty:
            return JsonResponse({'ok': False, 'error': f'Stock insuficiente para {p.name}.'})

        p.stock -= qty
        p.save(update_fields=['stock'])

        venta = Sale.objects.create(
            product=p, size=size, quantity=qty,
            unit_price=p.price, total=p.price * qty,
            source='local',
        )
        ventas_creadas.append(venta.id)

    return JsonResponse({'ok': True, 'ventas': ventas_creadas})


# ── Reporte Excel semanal ─────────────────────────────────────────────────────

@login_required(login_url='/panel/login/')
def panel_enviar_reporte(request):
    hoy    = timezone.now().date()
    inicio = hoy - timedelta(days=7)
    sales  = Sale.objects.filter(created_at__date__gte=inicio).select_related('product', 'size')

    # Crear Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Ventas Semanales'
    ws.append(['Fecha', 'Producto', 'Talla', 'Cantidad', 'Precio Unitario', 'Total', 'Origen'])
    for s in sales:
        ws.append([
            s.created_at.strftime('%d/%m/%Y %H:%M'),
            s.product.name if s.product else '—',
            s.size.name if s.size else '—',
            s.quantity,
            float(s.unit_price),
            float(s.total),
            s.get_source_display(),
        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Enviar correo
    try:
        msg = MIMEMultipart()
        msg['From']    = settings.EMAIL_HOST_USER
        msg['To']      = settings.ADMIN_EMAIL
        msg['Subject'] = f'Reporte Semanal Brana — {inicio} al {hoy}'
        msg.attach(MIMEText('Adjunto el reporte de ventas de la semana. 🌸', 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(buffer.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="reporte_{hoy}.xlsx"')
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, settings.ADMIN_EMAIL, msg.as_string())

        return JsonResponse({'ok': True, 'message': 'Reporte enviado correctamente.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})