from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, PromoCode, Advertisement,DeliverySettings


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'show_on_home', 'show_in_footer')
    list_editable = ('show_on_home', 'show_in_footer')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'discount_price', 'stock', 'is_active', 'is_best_selling', 'is_flash_sale', 'flash_sale_end', 'is_combo_offer')
    list_filter = ('category', 'is_active', 'is_best_selling', 'is_flash_sale', 'is_combo_offer')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock', 'is_active', 'is_best_selling', 'is_flash_sale', 'is_combo_offer')
    inlines = [ProductImageInline]



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'full_name', 'phone', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_id', 'full_name', 'phone')
    inlines = [OrderItemInline]
    list_editable = ('status',)



@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'max_discount_amount', 'is_active', 'valid_till')
    list_editable = ('is_active',)
    search_fields = ('code',)



@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'created_at')
    list_editable = ('is_active', 'order')




@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    list_display = ('dhaka_label', 'dhaka_charge', 'outside_label', 'outside_charge')

    def has_add_permission(self, request):
        return not DeliverySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False