import unicodedata
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from store.models import Product, Size


def clean_slug(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    from django.utils.text import slugify
    return slugify(text)


PLACEHOLDER = {
    'deportivo': 'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&q=80',
    'casual':    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=400&q=80',
    'accesorio': 'https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=400&q=80',
}

SEED_PRODUCTS = [
    # Mujer / Deportivo
    dict(name='Leggings Acanalados',       gender='mujer', style='deportivo', price=149.00, stock=30, description='Leggings de tiro alto con textura acanalada, control de abdomen.'),
    dict(name='Falda Deportiva Plisada',   gender='mujer', style='deportivo', price=129.00, stock=20, description='Falda plisada con short interior, perfecta para tenis o golf.'),
    dict(name='Short Runner',              gender='mujer', style='deportivo', price=99.00,  stock=25, description='Short ligero con bolsillos laterales y cintura elastica.'),
    dict(name='Licra Ciclista Suave',      gender='mujer', style='deportivo', price=139.00, stock=18, description='Licra ciclista hasta la rodilla, tela compresiva suave.'),
    dict(name='Vestido Deportivo Active',  gender='mujer', style='deportivo', price=189.00, stock=12, description='Vestido con soporte integrado, ideal para entrenamientos.'),
    dict(name='Banda Floral para Cabello', gender='mujer', style='deportivo', price=39.00,  stock=50, description='Banda antideslizante con estampado floral pastel.'),
    dict(name='Top Deportivo con Nudo',    gender='mujer', style='deportivo', price=119.00, stock=22, description='Top con nudo frontal y espalda abierta, soporte medium.'),
    # Mujer / Casual
    dict(name='Pantalon Mom Jeans',        gender='mujer', style='casual', price=229.00, stock=15, description='Mom jeans tiro alto con lavado vintage, 5 bolsillos.'),
    dict(name='Camisa Lino Oversize',      gender='mujer', style='casual', price=179.00, stock=20, description='Camisa de lino oversize, manga larga enrollable.'),
    dict(name='Vestido Midi Floral',       gender='mujer', style='casual', price=249.00, stock=10, description='Vestido midi con estampado floral, escote en V y tirantes.'),
    dict(name='Conjunto Cargo Mujer',      gender='mujer', style='casual', price=299.00, stock=8,  description='Conjunto de pantalon cargo y crop top a juego.'),
    dict(name='Blusa Francesa Puff',       gender='mujer', style='casual', price=159.00, stock=18, description='Blusa con mangas abullonadas estilo frances, cuello redondo.'),
    # Accesorios
    dict(name='Termo Acero 500ml',         gender='accesorio', style='accesorio', price=189.00, stock=30, description='Termo de acero inoxidable, mantiene frio 24h y calor 12h.'),
    dict(name='Aretes Perla Minimalistas', gender='accesorio', style='accesorio', price=79.00,  stock=40, description='Aretes de perla sintetica con base dorada.'),
    dict(name='Sandalias Planas Trenza',   gender='accesorio', style='accesorio', price=199.00, stock=14, description='Sandalias de tiras trenzadas en color arena.'),
    dict(name='Tenis Chunky Blanco',       gender='accesorio', style='accesorio', price=349.00, stock=9,  description='Tenis chunky sole gruesa, diseno minimalista blanco.'),
    dict(name='Set Pinzas Mariposa',       gender='accesorio', style='accesorio', price=59.00,  stock=60, description='Set de 6 pinzas mariposa en tonos pastel.'),
    dict(name='Pines Crocs Flores',        gender='accesorio', style='accesorio', price=49.00,  stock=80, description='Pack de 3 pines jibbitz con diseno floral para Crocs.'),
    dict(name='Pulsera Charm Dorada',      gender='accesorio', style='accesorio', price=89.00,  stock=35, description='Pulsera dorada con charms intercambiables.'),
]

SIZE_MAP = {
    'deportivo': ['XS', 'S', 'M', 'L', 'XL'],
    'casual':    ['XS', 'S', 'M', 'L', 'XL'],
    'accesorio': [],
}


def _fetch_image(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return ContentFile(r.content)
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Poblar la base de datos con productos de ejemplo para Brana.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Iniciando seed de Brana Clothes & More...'))

        size_names = ['XS', 'S', 'M', 'L', 'XL']
        sizes = {}
        for sn in size_names:
            obj, created = Size.objects.get_or_create(name=sn)
            sizes[sn] = obj
            if created:
                self.stdout.write(f'  Talla creada: {sn}')

        created_count = 0
        for data in SEED_PRODUCTS:
            style_key = data['style']
            slug_base = clean_slug(data['name'])

            if Product.objects.filter(slug=slug_base).exists():
                self.stdout.write(f'  Ya existe: {data["name"]} (omitido)')
                continue

            img_url  = PLACEHOLDER.get(style_key, PLACEHOLDER['casual'])
            img_file = _fetch_image(img_url)

            p = Product(
                name        = data['name'],
                slug        = slug_base,
                description = data['description'],
                price       = data['price'],
                stock       = data['stock'],
                gender      = data['gender'],
                style       = style_key,
                is_active   = True,
            )

            if img_file:
                p.image.save(f"{slug_base}.jpg", img_file, save=False)

            p.save()

            for size_name in SIZE_MAP.get(style_key, []):
                p.sizes.add(sizes[size_name])

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'  Producto creado: {p.name}'))

        self.stdout.write(self.style.SUCCESS(f'\nSeed completado. {created_count} productos creados.'))