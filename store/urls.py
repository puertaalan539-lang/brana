from django.urls import path
from . import views, panel_views, auth_views

app_name = 'store'

urlpatterns = [
    # ── Tienda pública ──────────────────────────────────────────
    path('',                      views.catalog,           name='catalog'),
    path('producto/<slug:slug>/', views.product_detail,    name='product_detail'),
    path('carrito/',              views.cart_view,         name='cart'),
    path('api/cart/add/',         views.cart_add,          name='cart_add'),
    path('api/cart/remove/',      views.cart_remove,       name='cart_remove'),
    path('api/order/confirm/',    views.confirm_order,     name='confirm_order'),

    # ── Auth usuarios ───────────────────────────────────────────
    path('cuenta/registro/',      auth_views.user_register, name='register'),
    path('cuenta/login/',         auth_views.user_login,    name='login'),
    path('cuenta/logout/',        auth_views.user_logout,   name='logout'),
    path('cuenta/perfil/',        auth_views.user_profile,  name='profile'),

    # ── Panel admin personalizado ───────────────────────────────
    path('panel/login/',                      panel_views.panel_login,           name='panel_login'),
    path('panel/logout/',                     panel_views.panel_logout,          name='panel_logout'),
    path('panel/inventario/',                 panel_views.panel_inventario,      name='panel_inventario'),
    path('panel/inventario/crear/',           panel_views.panel_producto_crear,  name='panel_producto_crear'),
    path('panel/inventario/editar/<int:pk>/', panel_views.panel_producto_editar, name='panel_producto_editar'),
    path('panel/inventario/stock/<int:pk>/',  panel_views.panel_stock_ajustar,   name='panel_stock_ajustar'),
    path('panel/ventas/',                     panel_views.panel_ventas,          name='panel_ventas'),
    path('panel/ventas/buscar/',              panel_views.panel_buscar_producto, name='panel_buscar_producto'),
    path('panel/ventas/registrar/',           panel_views.panel_registrar_venta, name='panel_registrar_venta'),
    path('panel/reporte/',                    panel_views.panel_enviar_reporte,  name='panel_enviar_reporte'),
    path('panel/pedidos/',                    panel_views.panel_pedidos,         name='panel_pedidos'),
    path('panel/pedidos/buscar/',             panel_views.panel_buscar_pedido,   name='panel_buscar_pedido'),
]