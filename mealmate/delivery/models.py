from django.db import models

# Create your models here.
class Customer(models.Model):
    username = models.CharField(max_length = 20)
    password = models.CharField(max_length = 20)
    email = models.CharField(max_length = 50)
    mobile = models.CharField(max_length = 15)
    address = models.CharField(max_length = 200) 
    
class Restaurant(models.Model):
    name = models.CharField(max_length = 50)
    picture = models.URLField(max_length = 500, default='https://cdn-icons-png.flaticon.com/256/6643/6643359.png')
    cuisine = models.CharField(max_length = 200)
    rating = models.FloatField()

class Item(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete = models.CASCADE, related_name = "items")
    name = models.CharField(max_length = 50)
    description = models.CharField(max_length = 300)
    price = models.FloatField()
    vegeterian = models.BooleanField(default=False)
    picture = models.URLField(max_length = 500, default='https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg')

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = "cart")
    items = models.ManyToManyField("Item", related_name = "carts", blank=True)

    def total_price(self):
        cart_items = self.cart_items.all()
        if cart_items.exists():
            return round(sum(ci.line_total() for ci in cart_items), 2)
        return round(sum(item.price for item in self.items.all()), 2)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="cart_entries")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'item')

    def line_total(self):
        return round(self.item.price * self.quantity, 2)

    # Helper properties for seamless template access
    @property
    def name(self):
        return self.item.name

    @property
    def description(self):
        return self.item.description

    @property
    def picture(self):
        return self.item.picture

    @property
    def price(self):
        return self.item.price

    @property
    def restaurant(self):
        return self.item.restaurant

    @property
    def vegeterian(self):
        return self.item.vegeterian
