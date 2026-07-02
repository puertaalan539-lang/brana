from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.auth.models import User
import unicodedata
import random


def clean_slug(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return slugify(text)


def generar_codigo_pedido():
    """Genera un código único de 4 dígitos para el pedido."""
    while True:
        codigo = str(random.randint(1000, 9999))
        if not Order.objects.filter(code=codigo).exists():
            return codigo


class Size(models.Model):
    name = models.CharField(max_length=5)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class Product(models.Model):
    GENDER_CHOICES = [
        ('mujer',     'Mujer'),
        ('hombre',    'Hombre'),
        ('nino',      'Nino'),
        ('unisex',    'Unisex'),
        ('accesorio', 'Accesorio'),
    ]

    STYLE_CHOICES = [
        ('deportivo', 'Deportivo'),
        ('casual',    'Casual'),
        ('elegante',  'Elegante'),
        ('accesorio', 'Accesorio'),
    ]

    name        = models.CharField(max_length=200, verbose_name="Nombre")
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(verbose_name="Descripcion", blank=True)
    price       = models.DecimalField(
        max_digits=7, decimal_places=2,
        validators=[MinValueValidator(30.00), MaxValueValidator(350.00)],
        verbose_name="Precio"
    )
    stock       = models.PositiveIntegerField(default=0, verbose_name="Stock general")
    image       = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Imagen")
    is_active   = models.BooleanField(default=True, verbose_name="Activo")
    gender      = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="Genero")
    style       = models.CharField(max_length=10, choices=STYLE_CHOICES, verbose_name="Estilo")
    sizes       = models.ManyToManyField(Size, blank=True, verbose_name="Tallas")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = clean_slug(self.name)
            slug = base_slug
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Producto"
        verbose_name_plural = "Productos"


class Sale(models.Model):
    SOURCE_CHOICES = [
        ('local',  'Venta Local'),
        ('online', 'Venta Online'),
    ]

    product    = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Producto")
    size       = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Talla")
    quantity   = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    unit_price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Precio unitario")
    total      = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="Total")
    source     = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='local', verbose_name="Origen")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    def __str__(self):
        return f"{self.product} x{self.quantity} - ${self.total} ({self.get_source_display()})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"


# ── Pedidos para recoger en tienda ──────────────────────────────────────────

class Order(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('listo',     'Listo para recoger'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    code       = models.CharField(max_length=4, unique=True, default=generar_codigo_pedido, verbose_name="Codigo")
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Cliente")
    total      = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="Total")
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendiente', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del pedido")

    def __str__(self):
        return f"Pedido #{self.code} — {self.user} — ${self.total}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    size       = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    quantity   = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=7, decimal_places=2)
    subtotal   = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    class Meta:
        verbose_name = "Producto del pedido"
        verbose_name_plural = "Productos del pedido"