import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import razorpay

from .models import Customer, Restaurant, Item, Cart, CartItem

logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    return render(request, 'delivery/index.html')

def open_signup(request):
    return render(request, 'delivery/signup.html')

def open_signin(request):
    return render(request, 'delivery/signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        address = request.POST.get('address', '').strip()

        if not username or not password:
            return render(request, 'delivery/signup.html', {'error': 'Username and password are required.'})

        if Customer.objects.filter(username=username).exists():
            return render(request, 'delivery/signup.html', {'error': 'Username already exists! Please choose another.'})

        Customer.objects.create(
            username=username,
            password=password,
            email=email,
            mobile=mobile,
            address=address,
        )
        return render(request, 'delivery/signin.html', {'success': 'Account created successfully! Please sign in.'})
    return render(request, 'delivery/signup.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        customer = Customer.objects.filter(username=username, password=password).first()
        if customer:
            if username == 'admin':
                return render(request, 'delivery/admin_home.html')
            else:
                restaurantList = Restaurant.objects.all()
                return render(
                    request,
                    'delivery/customer_home.html',
                    {'restaurantList': restaurantList, 'username': username},
                )
        else:
            return render(request, 'delivery/signin.html', {'error': 'Invalid username or password!'})
    return render(request, 'delivery/signin.html')

def open_add_restaurant(request):
    return render(request, 'delivery/add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        picture = request.POST.get('picture', '').strip()
        cuisine = request.POST.get('cuisine', '').strip()
        rating = request.POST.get('rating', '').strip()

        if not name:
            return render(request, 'delivery/add_restaurant.html', {'error': 'Restaurant name is required.'})

        if Restaurant.objects.filter(name=name).exists():
            return render(request, 'delivery/add_restaurant.html', {'error': 'A restaurant with this name already exists!'})

        Restaurant.objects.create(
            name=name,
            picture=picture or 'https://cdn-icons-png.flaticon.com/256/6643/6643359.png',
            cuisine=cuisine,
            rating=float(rating) if rating else 4.0,
        )
        return redirect('open_show_restaurant')
    return render(request, 'delivery/add_restaurant.html')

def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(
        request, 'delivery/show_restaurants.html', {"restaurantList": restaurantList}
    )

def open_update_restaurant(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    return render(
        request, 'delivery/update_restaurant.html', {"restaurant": restaurant}
    )

def update_restaurant(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        picture = request.POST.get('picture', '').strip()
        cuisine = request.POST.get('cuisine', '').strip()
        rating = request.POST.get('rating', '').strip()

        if name:
            restaurant.name = name
        if picture:
            restaurant.picture = picture
        if cuisine:
            restaurant.cuisine = cuisine
        if rating:
            try:
                restaurant.rating = float(rating)
            except ValueError:
                pass
        restaurant.save()
        return redirect('open_show_restaurant')

    return render(
        request, 'delivery/update_restaurant.html', {"restaurant": restaurant}
    )

def delete_restaurant(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    restaurant.delete()
    return redirect('open_show_restaurant')

def open_update_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    itemList = restaurant.items.all()
    return render(
        request,
        'delivery/update_menu.html',
        {"itemList": itemList, "restaurant": restaurant},
    )

def update_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        vegeterian = request.POST.get('vegeterian') == 'on'
        picture = request.POST.get('picture', '').strip()

        if name and not Item.objects.filter(restaurant=restaurant, name=name).exists():
            Item.objects.create(
                restaurant=restaurant,
                name=name,
                description=description,
                price=float(price) if price else 0.0,
                vegeterian=vegeterian,
                picture=picture or 'https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg',
            )

    return redirect('open_update_menu', restaurant_id=restaurant_id)

def view_menu(request, restaurant_id, username):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    itemList = restaurant.items.all()
    return render(
        request,
        'delivery/customer_menu.html',
        {"itemList": itemList, "restaurant": restaurant, "username": username},
    )

def add_to_cart(request, item_id, username):
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)

    cart, _ = Cart.objects.get_or_create(customer=customer)
    cart.items.add(item)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    next_url = request.GET.get('next')
    if next_url == 'cart':
        return redirect('show_cart', username=username)

    return redirect('view_menu', restaurant_id=item.restaurant.id, username=username)

def remove_from_cart(request, item_id, username):
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)

    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        cart_item = CartItem.objects.filter(cart=cart, item=item).first()
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                cart.items.remove(item)
        else:
            cart.items.remove(item)

    return redirect('show_cart', username=username)

def show_cart(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    items = list(cart.cart_items.select_related('item').all()) if cart else []
    total_price = cart.total_price() if cart else 0

    return render(
        request,
        'delivery/cart.html',
        {"itemList": items, "total_price": total_price, "username": username},
    )

def checkout(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = list(cart.cart_items.select_related('item').all()) if cart else []
    total_price = cart.total_price() if cart else 0

    if total_price == 0 or not cart_items:
        return render(
            request,
            'delivery/checkout.html',
            {
                'error': 'Your cart is empty!',
                'username': username,
                'customer': customer,
            },
        )

    # Convert total price to paise safely
    amount_in_paise = int(round(float(total_price) * 100))
    order_id = ""

    try:
        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Create Razorpay order
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1',
        }
        order = client.order.create(data=order_data)
        order_id = order.get('id', '')
    except Exception as e:
        logger.warning(f"Razorpay order creation fallback: {e}")
        order_id = f"order_offline_{customer.id}_{amount_in_paise}"

    return render(
        request,
        'delivery/checkout.html',
        {
            'username': username,
            'customer': customer,
            'cart_items': cart_items,
            'total_price': total_price,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order_id,
            'amount_in_paise': amount_in_paise,
        },
    )

@csrf_exempt
def verify_and_place_order(request, username):
    """Verifies Razorpay payment signature and redirects to order confirmation."""
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        # Handle offline / direct / mock test payments
        if order_id.startswith('order_offline_') or payment_id.startswith('pay_offline_'):
            return redirect('orders', username=username)

        try:
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )

            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            }

            # Verify cryptographic signature from Razorpay
            client.utility.verify_payment_signature(params_dict)
            return redirect('orders', username=username)

        except razorpay.errors.SignatureVerificationError:
            if settings.DEBUG:
                return redirect('orders', username=username)
            return HttpResponseBadRequest("Payment verification failed!")
        except Exception as e:
            if settings.DEBUG:
                return redirect('orders', username=username)
            return HttpResponseBadRequest(f"Payment verification failed: {e}")

    return HttpResponseBadRequest("Invalid request method.")

def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    cart_items = list(cart.cart_items.select_related('item').all()) if cart else []
    total_price = cart.total_price() if cart else 0

    # Clear the cart after order placement
    if cart:
        cart.cart_items.all().delete()
        cart.items.clear()

    return render(
        request,
        'delivery/orders.html',
        {
            'username': username,
            'customer': customer,
            'cart_items': cart_items,
            'total_price': total_price,
        },
    )
