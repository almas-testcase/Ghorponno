from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(
        upload_to='categories/', blank=True, null=True,
        help_text="Recommended size: 400x400px (square, 1:1 ratio). White or transparent background looks best."
    )
    show_on_home = models.BooleanField(default=False, help_text="Homepage-e top category card e dekhabe")
    show_in_footer = models.BooleanField(default=False, help_text="Footer er 'Explore Products' e dekhabe")
    
    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    weight = models.CharField(max_length=50, blank=True, help_text="e.g. 250g, 500g, 1.0kg")
    search_keywords = models.CharField(
        max_length=255, blank=True,
        help_text="Alternate/Bangla spellings for search, comma separated. e.g. চাল, chal, rice"
    )
    is_flash_sale = models.BooleanField(default=False, help_text="Check korle eta flash sale e dekhabe")
    flash_sale_end = models.DateTimeField(
        blank=True, null=True,
        help_text="Flash sale kokhon shesh hobe (deadline). is_flash_sale checked thakle eta filup koro."
    )
    is_best_selling = models.BooleanField(default=False, help_text="Check korle 'Best Selling Products' section e dekhabe")
    is_combo_offer = models.BooleanField(default=False, help_text="Check korle Combo Offer page e dekhabe")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(
        upload_to='products/', blank=True, null=True,
        help_text="Recommended size: 1000x1000px (square, 1:1 ratio). White/plain background looks best. Higher resolution keeps the zoom-on-hover feature sharp."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):                       # <-- নতুন
        if self.discount_price and self.price:
            return round((1 - (self.discount_price / self.price)) * 100)
        return 0

    @property
    def final_price(self):                             # <-- নতুন
        return self.discount_price if self.discount_price else self.price

    def __str__(self):
        return self.name



class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='products/gallery/',
        help_text="Recommended size: 1000x1000px (square, 1:1 ratio), same style as main image."
    )
    order = models.PositiveIntegerField(default=0, help_text="Choto number age dekhabe")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"



class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    DELIVERY_AREA_CHOICES = (
        ('dhaka', 'Inside Dhaka (৳80)'),
        ('outside', 'Outside Dhaka (৳140)'),
    )

    order_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)        
    address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    promo_code = models.CharField(max_length=30, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    delivery_area = models.CharField(max_length=10, choices=DELIVERY_AREA_CHOICES, default='dhaka')
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=80)

    def __str__(self):
        return self.order_id
        


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # order er somoy er price

    def __str__(self):
        return f"{self.product} x {self.quantity}"



class PromoCode(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField(help_text="e.g. 10 for 10% off")
    is_active = models.BooleanField(default=True)
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Optional cap, e.g. max ৳100 discount"
    )
    valid_till = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"


class Advertisement(models.Model):
    title = models.CharField(max_length=150, help_text="Internal name, e.g. 'Sidebar Ad 1'")
    image = models.ImageField(upload_to='ads/')
    link = models.URLField(blank=True, help_text="Optional - click korle kothay jabe")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Choto number age dekhabe")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title



class DeliverySettings(models.Model):
    dhaka_label = models.CharField(max_length=100, default="Inside Dhaka")
    dhaka_charge = models.DecimalField(max_digits=10, decimal_places=2, default=80)
    outside_label = models.CharField(max_length=100, default="Outside Dhaka")
    outside_charge = models.DecimalField(max_digits=10, decimal_places=2, default=140)

    class Meta:
        verbose_name = "Delivery Charge"
        verbose_name_plural = "Delivery Charge Settings"

    def __str__(self):
        return "Delivery Charge Settings"

    def save(self, *args, **kwargs):
        self.pk = 1          # শুধু 1 টা row-ই থাকবে (singleton)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass                  # accidentally delete হওয়া থেকে বাঁচাবে

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj