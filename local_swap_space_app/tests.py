from datetime import datetime

from PIL import Image
from io import BytesIO
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Avg
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from local_swap_space_app.models import Category, Item, ItemImage, User, Like, Match, Rating
from .forms import ItemForm, ItemImageForm
from .views import MatchUserListView


class TestDashboardView(TestCase):
    def setUp(self):
        # Create a user with a location
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='12345',
            latitude=50.0646501,
            longitude=19.9449799
        )
        # User should have location set automatically by the save method in the User model
        self.user.save()

        self.category = Category.objects.create(name="Electronics")

        # Create 5 items for this user
        self.items = [
            Item.objects.create(
                name=f"Item {i}",
                category=self.category,
                owner=self.user
            ) for i in range(5)
        ]

    def test_access_dashboard_unauthenticated(self):
        # Test to ensure redirect when unauthenticated
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_filter_by_category(self):
        self.client.login(username='testuser', password='12345')
        category2 = Category.objects.create(name="Books")
        Item.objects.create(name="Book 1", category=category2, owner=self.user)
        response = self.client.get(reverse('dashboard'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item.category == self.category for item in response.context['items']))

    def test_dashboard_filter_by_distance(self):
        self.client.login(username='testuser', password='12345')
        # Create another user with items at a different location
        other_user = get_user_model().objects.create_user(
            username='otheruser',
            password='12345',
            latitude=50.037908,  # Nearby location
            longitude=19.940984
        )
        category2 = Category.objects.create(name="Clothes")
        Item.objects.create(name="Shirt", category=category2, owner=other_user)
        # Max distance that includes the created item
        response = self.client.get(reverse('dashboard'), {'distance': '10'})  # 10 kilometers
        self.assertEqual(response.status_code, 200)
        self.assertIn('Shirt', [item.name for item in response.context['items']])


class TestMatchUserListView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='user', password='test')
        self.view = MatchUserListView()

    def test_get_queryset_no_matches(self):
        request = self.factory.get('/fake-url')
        request.user = self.user
        self.view.request = request

        result = self.view.get_queryset()
        self.assertEqual(len(result), 0, "Expected empty list when no matches exist.")


class ItemDetailViewTests(TestCase):
    def setUp(self):
        # Creating a user
        self.user = User.objects.create_user(username='testuser', password='12345')

        # Creating a category for items
        self.category = Category.objects.create(name='Electronics')

        # Creating an item owned by the user
        self.item = Item.objects.create(
            name="Laptop",
            description="A high performance laptop.",
            category=self.category,
            owner=self.user,
            status='AVAILABLE'
        )

    def test_detail_view_with_authenticated_user(self):
        # Log the user in
        self.client.login(username='testuser', password='12345')

        # Get the response from accessing the item detail view
        response = self.client.get(reverse('item-detail', kwargs={'pk': self.item.pk}))

        # Check that the response is successful (HTTP 200)
        self.assertEqual(response.status_code, 200)
        # Verify that the correct template is used
        self.assertTemplateUsed(response, 'item_detail.html')
        # Check if the item's context data is correctly passed to the template
        self.assertEqual(response.context['item'].id, self.item.id)

    def test_detail_view_without_authenticated_user(self):
        # Attempt to access the item detail view without logging in
        response = self.client.get(reverse('item-detail', kwargs={'pk': self.item.pk}))

        # Check that the response is a redirect to the login page (HTTP 302)
        self.assertEqual(response.status_code, 302)
        # Check the redirect location (typically, this should redirect to the login page)
        self.assertTrue(response.url.startswith('/login/'))


class AddItemViewTest(TestCase):
    def setUp(self):
        # Create a user
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client = Client()
        self.client.login(username='testuser', password='12345')

    def test_get_method(self):
        # Access the view
        response = self.client.get(reverse('add_item'))  # Ensure you have the correct URL name in your urls.py
        self.assertEqual(response.status_code, 200)
        # Check if the correct templates were used
        self.assertTemplateUsed(response, 'add_item.html')
        # Check if the forms are in the context
        self.assertIn('item_form', response.context)
        self.assertIn('image_form', response.context)


class AddItemPostTest(TestCase):
    def setUp(self):
        # Setup code here
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.category = Category.objects.create(name='Electronics')

    def test_post_valid_data(self):
        # Create an in-memory image
        image = Image.new('RGB', (100, 100), 'red')
        image_file = BytesIO()
        image.save(image_file, format='JPEG')
        image_file.seek(0)
        uploaded_image = SimpleUploadedFile("test_image.jpg", image_file.getvalue(), content_type="image/jpeg")

        # Form data
        data = {
            'name': 'New Camera',
            'description': 'A brand new DSLR camera.',
            'category': self.category.id,
            'status': 'AVAILABLE',
            'image': uploaded_image
        }

        # Making a POST request
        response = self.client.post(reverse('add_item'), data)
        self.assertEqual(response.status_code, 302)

        # Assertions for redirect and object creation
        item = Item.objects.get(name='New Camera')
        self.assertRedirects(response, reverse('item-detail', kwargs={'pk': item.pk}))
        self.assertTrue(Item.objects.filter(name='New Camera').exists())
        self.assertTrue(ItemImage.objects.filter(item=item).exists())


class ItemUpdateViewTests(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Electronics')
        # Create an item owned by the user
        self.item = Item.objects.create(
            name='Old Camera',
            description='A rare vintage camera',
            category=self.category,
            owner=self.user,
            status='AVAILABLE'
        )
        self.url = reverse('edit_item', kwargs={'pk': self.item.pk})

    def test_access_control(self):
        # Attempt to access the update page without authentication
        response = self.client.get(self.url)
        # Expect a redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

        # Now test with authenticated user
        self.client.login(username='testuser', password='12345')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_form_submission_with_valid_data(self):
        self.client.login(username='testuser', password='12345')
        # Note that 'name' is included here to demonstrate that even though it's sent, it shouldn't change.
        data = {
            'name': 'New Camera',  # Attempt to update name, but should be ignored
            'description': 'An updated description',
            'category': self.category.id,
            'status': 'RESERVED'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)  # Expecting redirect after successful submission

        # Fetch the updated item
        updated_item = Item.objects.get(pk=self.item.pk)
        # Check that the name has NOT changed as it is non-editable
        self.assertEqual(updated_item.name, 'Old Camera')  # Correct assertion based on your setup
        self.assertEqual(updated_item.description, 'An updated description')
        self.assertEqual(updated_item.status, 'RESERVED')

    def test_form_submission_with_invalid_data(self):
        self.client.login(username='testuser', password='12345')
        data = {
            'name': '',  # Ignored due to non-editability
            'description': '',  # Invalid data: empty description
            'category': self.category.id,
            'status': 'RESERVED'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)  # Should stay on the same page due to form errors
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('description', response.context['form'].errors)  # Error should now focus on 'description'


class AddImageViewTests(TestCase):
    def setUp(self):
        # Create a user and log them in
        self.user = get_user_model().objects.create_user(username='testuser', password='123password')
        self.client.login(username='testuser', password='123password')
        # Assume a Category model exists and is required by the Item model
        self.category = Category.objects.create(name='Test Category')
        # Create an item with all required fields, including the newly created category
        self.item = Item.objects.create(
            name='Test Item',
            description='Test Description',
            owner=self.user,
            category=self.category  # Ensure the category is assigned here
        )
        # URL to your image upload view
        self.url = reverse('add_image', kwargs={'pk': self.item.pk})

    def test_successful_image_upload(self):
        # Create an in-memory image
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, format='JPEG')
        image_file.seek(0)

        # Prepare image data with Django's SimpleUploadedFile
        image_data = SimpleUploadedFile('image.jpg', image_file.read(), content_type='image/jpeg')
        # Post the image data to the view
        response = self.client.post(self.url, {'image': image_data})
        # Check if the user is redirected to the edit item page
        self.assertRedirects(response, reverse('edit_item', kwargs={'pk': self.item.pk}))
        # Verify that the image has been saved
        self.assertEqual(ItemImage.objects.count(), 1)
        self.assertTrue(ItemImage.objects.filter(item=self.item).exists())
        # Verify that a success message has been added
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Image added successfully!")

    def test_unsuccessful_image_upload_no_file_provided(self):
        response = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(response, reverse('edit_item', kwargs={'pk': self.item.pk}))
        self.assertEqual(ItemImage.objects.count(), 0)
        # Access messages from the context of the final response after following the redirect
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You must provide an image file.")


class DeleteImageViewTests(TestCase):
    def setUp(self):
        # Create a user and log them in
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        # Create a Category and Item
        self.category = Category.objects.create(name='Electronics')
        self.item = Item.objects.create(name='Camera', description='A nice camera.', category=self.category,
                                        owner=self.user)
        # Create an image for the item
        self.image = ItemImage.objects.create(item=self.item, image='path/to/image.jpg')
        self.url = reverse('delete_image', kwargs={'pk': self.image.pk})

    def test_delete_image_successfully(self):
        # Send POST request to delete the image
        response = self.client.post(self.url)
        # Check if the image was deleted
        self.assertFalse(ItemImage.objects.filter(pk=self.image.pk).exists())
        # Verify the user is redirected to the edit item page
        self.assertRedirects(response, reverse('edit_item', kwargs={'pk': self.item.pk}))
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Image deleted successfully!")

    def test_delete_image_unauthorized_user(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertTrue(ItemImage.objects.filter(pk=self.image.pk).exists())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.url = reverse('profile')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/login/?next={self.url}')

    def test_logged_in_uses_correct_template(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(self.url)

        # Check user is logged in
        self.assertEqual(str(response.context['user']), 'testuser')
        # Check a response "success"
        self.assertEqual(response.status_code, 200)
        # Check correct template
        self.assertTemplateUsed(response, 'profile.html')

        # Setup context data checks
        self.assertEqual(response.context['profile_user'], self.user)
        items = Item.objects.filter(owner=self.user)
        self.assertEqual(list(response.context['items']), list(items))

        # Assuming the Rating model is correctly linked and functioning
        average_rating = Rating.objects.filter(rated_user=self.user).aggregate(Avg('rating'))['rating__avg']
        average_rating = average_rating if average_rating is not None else "No ratings"
        self.assertEqual(response.context['average_rating'], average_rating)


class OtherUserProfileViewTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.category = Category.objects.create(name='Electronics')
        self.item = Item.objects.create(name='Sample Item', category=self.category, owner=self.user1)
        self.client.login(username='user1', password='testpass123')

    def test_get_context_data(self):
        response = self.client.get(reverse('other-user-profile', kwargs={'username': 'user2'}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile_user', response.context)
        self.assertEqual(response.context['profile_user'], self.user2)
        # Additional assertions for 'items', 'existing_rating', 'can_rate', 'average_rating'.
        self.assertIn('items', response.context)
        self.assertIn('existing_rating', response.context)
        self.assertIn('can_rate', response.context)
        self.assertIn('average_rating', response.context)

    def test_post_rating(self):
        like1 = Like.objects.create(item=self.item, liker=self.user1)
        like2 = Like.objects.create(item=self.item, liker=self.user2)
        Match.objects.create(like_one=like1, like_two=like2)

        # POST
        response = self.client.post(reverse('other-user-profile', kwargs={'username': 'user2'}), {
            'rating': 5
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(Rating.objects.first().rating, 5)

        # Second POST - New rating expected to overwrite the first
        response = self.client.post(reverse('other-user-profile', kwargs={'username': 'user2'}), {
            'rating': 3
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Rating.objects.count(), 1)  # Still only one rating should exist
        self.assertEqual(Rating.objects.first().rating, 3)  # Rating should be 3


class LikedItemsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='12345')
        self.user2 = User.objects.create_user(username='user2', password='12345')
        self.category = Category.objects.create(name="Electronics")
        self.item1 = Item.objects.create(name='Item1', description='Desc1', owner=self.user2, category=self.category)
        self.item2 = Item.objects.create(name='Item2', description='Desc2', owner=self.user2, category=self.category)

        # User likes some items
        Like.objects.create(item=self.item1, liker=self.user, liked_on=datetime.now())
        Like.objects.create(item=self.item2, liker=self.user, liked_on=datetime.now())

    def test_authentication_required(self):
        # Test access without authentication
        response = self.client.get(reverse('liked_items'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('liked_items')}")

    def test_correct_liked_items_displayed_for_authenticated_user(self):
        self.client.login(username='user1', password='12345')
        response = self.client.get(reverse('liked_items'))
        self.assertEqual(response.status_code, 200)
        likes_displayed = list(response.context['likes'])
        self.assertEqual(len(likes_displayed), 2)
        self.assertTrue(all(like.item in [self.item1, self.item2] for like in likes_displayed))
