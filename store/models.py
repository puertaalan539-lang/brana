from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
import unicodedata


def clean_slug(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return slugify(text)


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
        return f"{self.product} x{self.quantity} — ${self.total} ({self.get_source_display()})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"