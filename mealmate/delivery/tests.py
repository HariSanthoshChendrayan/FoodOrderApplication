from django.test import TestCase, Client
from django.urls import reverse
from .models import Customer, Restaurant, Item, Cart


class MealMateFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(
            username='testuser',
            password='password123',
            email='test@example.com',
            mobile='9876543210',
            address='123 Test Street',
        )
        self.admin_user = Customer.objects.create(
            username='admin',
            password='adminpassword',
            email='admin@example.com',
            mobile='1122334455',
            address='HQ Address',
        )
        self.restaurant = Restaurant.objects.create(
            name='Test Bistro',
            picture='https://example.com/bistro.jpg',
            cuisine='Italian',
            rating=4.5,
        )
        self.item = Item.objects.create(
            restaurant=self.restaurant,
            name='Pasta Alfredo',
            description='Creamy white sauce pasta',
            price=250.0,
            vegeterian=True,
            picture='https://example.com/pasta.jpg',
        )

    def test_landing_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meal Mate')

    def test_signup_flow(self):
        # GET signup
        response = self.client.get(reverse('open_signup'))
        self.assertEqual(response.status_code, 200)

        # Duplicate username
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'testuser',
                'password': 'newpass',
                'email': 'new@example.com',
                'mobile': '1234567890',
                'address': 'New Address',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username already exists')

        # Successful signup
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'newuser',
                'password': 'newpass',
                'email': 'new@example.com',
                'mobile': '1234567890',
                'address': 'New Address',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Customer.objects.filter(username='newuser').exists())

    def test_signin_flow(self):
        # GET signin
        response = self.client.get(reverse('signin'))
        self.assertEqual(response.status_code, 200)

        # Invalid login
        response = self.client.post(
            reverse('signin'),
            {'username': 'testuser', 'password': 'wrongpassword'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

        # Customer login
        response = self.client.post(
            reverse('signin'),
            {'username': 'testuser', 'password': 'password123'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Popular Restaurants')

        # Admin login
        response = self.client.post(
            reverse('signin'),
            {'username': 'admin', 'password': 'adminpassword'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_admin_restaurant_management(self):
        # Add restaurant
        response = self.client.post(
            reverse('add_restaurant'),
            {
                'name': 'New Diner',
                'picture': 'https://example.com/diner.jpg',
                'cuisine': 'American',
                'rating': '4.2',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Restaurant.objects.filter(name='New Diner').exists())

        diner = Restaurant.objects.get(name='New Diner')

        # Update restaurant
        response = self.client.post(
            reverse('update_restaurant', args=[diner.id]),
            {
                'name': 'New Diner Deluxe',
                'picture': 'https://example.com/diner2.jpg',
                'cuisine': 'American Gourmet',
                'rating': '4.8',
            },
        )
        self.assertEqual(response.status_code, 302)
        diner.refresh_from_db()
        self.assertEqual(diner.name, 'New Diner Deluxe')

        # Add item to menu
        response = self.client.post(
            reverse('update_menu', args=[diner.id]),
            {
                'name': 'Classic Burger',
                'description': 'Juicy beef patty',
                'price': '199',
                'vegeterian': '',
                'picture': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Item.objects.filter(restaurant=diner, name='Classic Burger').exists())

        # Delete restaurant
        response = self.client.get(reverse('delete_restaurant', args=[diner.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Restaurant.objects.filter(id=diner.id).exists())

    def test_cart_and_checkout_flow(self):
        # View menu
        response = self.client.get(reverse('view_menu', args=[self.restaurant.id, self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pasta Alfredo')

        # Add to cart redirects back to menu
        response = self.client.get(reverse('add_to_cart', args=[self.item.id, self.customer.username]))
        self.assertEqual(response.status_code, 302)

        # Check cart
        response = self.client.get(reverse('show_cart', args=[self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pasta Alfredo')
        self.assertContains(response, '250')

        # Checkout page loads safely without crashing on external APIs
        response = self.client.get(reverse('checkout', args=[self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pasta Alfredo')
        self.assertContains(response, '250')

        # Place order via offline / direct payment
        response = self.client.post(
            reverse('verify_and_place_order', args=[self.customer.username]),
            {
                'razorpay_order_id': 'order_offline_test',
                'razorpay_payment_id': 'pay_offline_test',
                'razorpay_signature': 'sig_offline',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders', args=[self.customer.username]))

        # Order summary page
        response = self.client.get(reverse('orders', args=[self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Successful')

        # Cart should now be empty
        cart = Cart.objects.get(customer=self.customer)
        self.assertEqual(cart.cart_items.count(), 0)

    def test_multiple_add_to_cart_and_quantity_control(self):
        # Add item first time
        self.client.get(reverse('add_to_cart', args=[self.item.id, self.customer.username]))
        # Add same item second time
        self.client.get(reverse('add_to_cart', args=[self.item.id, self.customer.username]))
        # Add same item third time with next=cart query param
        response = self.client.get(reverse('add_to_cart', args=[self.item.id, self.customer.username]) + '?next=cart')
        self.assertRedirects(response, reverse('show_cart', args=[self.customer.username]))

        cart = Cart.objects.get(customer=self.customer)
        cart_item = cart.cart_items.get(item=self.item)
        self.assertEqual(cart_item.quantity, 3)
        self.assertEqual(cart.total_price(), 750.0)

        # View cart template check
        response = self.client.get(reverse('show_cart', args=[self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '750')
        self.assertContains(response, '3')

        # Decrease quantity
        self.client.get(reverse('remove_from_cart', args=[self.item.id, self.customer.username]))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart.total_price(), 500.0)

        # Checkout with quantity = 2
        response = self.client.get(reverse('checkout', args=[self.customer.username]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '× 2')
        self.assertContains(response, '500')
