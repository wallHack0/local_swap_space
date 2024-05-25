import json
from datetime import datetime

from PIL import Image
from io import BytesIO
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Avg
from django.middleware.csrf import get_token
from django.test import TestCase, Client
from django.urls import reverse
from local_swap_space_app.models import Category, Item, ItemImage, User, Like, Match, Rating, Chat, Message
from django.contrib.gis.geos import Point


class RegisterViewTests(TestCase):
    def test_successful_registration_and_login(self):
        url = reverse('register')
        data = {
            'username': 'user',
            'email': 'user@example.com',
            'password1': 'strong_password_123',
            'password2': 'strong_password_123',
            'city': 'TestCity'
        }
        response = self.client.post(url, data)
        user = User.objects.get(username='user')
        # User should be logged-in after registration.
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertRedirects(response, reverse('dashboard'))

    def test_mismatched_passwords(self):
        url = reverse('register')
        data = {
            'username': 'user_test',
            'email': 'usertest@example.com',
            'password1': 'Password123',
            'password2': 'Password1234',  # Mismatch passwords.
            'city': 'TestCity',
            'latitude': '45.000',
            'longitude': '90.000'
        }
        response = self.client.post(url, data)
        # The user should not be created.
        self.assertFalse(get_user_model().objects.filter(username='user_test').exists())
        # The form should be rendered again with a password mismatch error.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two password fields didn’t match.")


class CustomLoginViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', email='test@example.com',
                                                         password='securepassword123')

    def test_successful_login(self):
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'securepassword123'
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(self.user.is_authenticated)

    def test_login_with_geolocation(self):
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'securepassword123',
            'latitude': '34.0522',
            'longitude': '-118.2437'
        }
        response = self.client.post(url, data)
        # Retrieve the updated user instance from the database
        user = get_user_model().objects.get(username='testuser')
        # Check if latitude and longitude are updated correctly
        self.assertAlmostEqual(float(user.latitude), 34.0522)
        self.assertAlmostEqual(float(user.longitude), -118.2437)
        self.assertRedirects(response, reverse('dashboard'))


class TestDashboardView(TestCase):
    def setUp(self):
        # Create a user with a location.
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='12345',
            latitude=50.0646501,
            longitude=19.9449799
        )
        # User should have location set automatically by the save method in the User model.
        self.user.save()

        self.category = Category.objects.create(name="Electronics")

        # Create 5 items for this user.
        self.items = [
            Item.objects.create(
                name=f"Item {i}",
                category=self.category,
                owner=self.user
            ) for i in range(5)
        ]

    def test_access_dashboard_unauthenticated(self):
        # Test to ensure redirect when unauthenticated.
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
        # Create another user with items at a different location.
        other_user = get_user_model().objects.create_user(
            username='otheruser',
            password='12345',
            latitude=50.037908,  # Nearby location.
            longitude=19.940984
        )
        category2 = Category.objects.create(name="Clothes")
        Item.objects.create(name="Shirt", category=category2, owner=other_user)
        # Max distance that includes the created item.
        response = self.client.get(reverse('dashboard'), {'distance': '10'})  # 10 kilometers.
        self.assertEqual(response.status_code, 200)
        self.assertIn('Shirt', [item.name for item in response.context['items']])


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
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Electronics')
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
        self.user = get_user_model().objects.create_user(username='testuser', password='123password')
        self.client.login(username='testuser', password='123password')
        self.category = Category.objects.create(name='Test Category')
        self.item = Item.objects.create(
            name='Test Item',
            description='Test Description',
            owner=self.user,
            category=self.category
        )
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
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.category = Category.objects.create(name='Electronics')
        self.item = Item.objects.create(name='Camera', description='A nice camera.', category=self.category,
                                        owner=self.user)
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


class DeleteItemViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.category = Category.objects.create(name='Test Category')
        self.item = Item.objects.create(name='Test Item', description='Test description', category=self.category,
                                        owner=self.user)

    def test_delete_item_owner(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('delete_item', kwargs={'item_id': self.item.id}))
        self.assertFalse(Item.objects.filter(pk=self.item.id).exists())

    def test_delete_item_not_owner(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        self.client.login(username='otheruser', password='otherpassword')
        response = self.client.post(reverse('delete_item', kwargs={'item_id': self.item.id}))
        self.assertTrue(Item.objects.filter(pk=self.item.id).exists())


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


class MatchUserListViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.user3 = User.objects.create_user(username='user3', password='password123')
        self.category = Category.objects.create(name="Toys")
        self.item1 = Item.objects.create(name='Item1', description='Desc1', owner=self.user1, category=self.category)
        self.item2 = Item.objects.create(name='Item2', description='Desc2', owner=self.user2, category=self.category)
        self.item3 = Item.objects.create(name='Item3', description='Desc3', owner=self.user3, category=self.category)
        self.like1 = Like.objects.create(item=self.item1, liker=self.user2)
        self.like2 = Like.objects.create(item=self.item2, liker=self.user1)
        self.match1 = Match.objects.create(like_one=self.like1, like_two=self.like2)

        self.client = Client()

    def test_authentication_required(self):
        # Attempt to access the view without being logged in
        response = self.client.get(reverse('match_list'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('match_list')}")

    def test_queryset_correctly_filtered(self):
        # Login and access the view
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('match_list'))
        self.assertEqual(response.status_code, 200)
        # Check the context contains the correct matches
        matches = response.context['matches']
        self.assertEqual(len(matches), 1)
        self.assertTrue(any(match['other_user'] == self.user2 for match in matches))

    def test_grouping_and_chat_session_creation(self):
        # Ensure no chats exist initially, clearing any possibly auto-created chats in setUp
        Chat.objects.all().delete()
        self.assertEqual(Chat.objects.count(), 0)
        # Login and access the view
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('match_list'))
        # Assumption: `match_list` view might be creating a chat session if matches exist
        matches = response.context['matches']
        chat_created = any(match['chat'] is not None for match in matches)
        # Validate that a chat session was created
        self.assertTrue(chat_created)
        self.assertEqual(Chat.objects.count(), 1)


class ChatViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.user3 = User.objects.create_user(username='user3', password='password123')

        # Create a chat between user1 and user2
        self.chat = Chat.objects.create(participant_one=self.user1, participant_two=self.user2)
        self.message1 = Message.objects.create(chat=self.chat, sender=self.user1, text="Hello, how are you?")
        self.message2 = Message.objects.create(chat=self.chat, sender=self.user2, text="I'm fine, thank you!")

        self.client = Client()

    def test_access_restriction(self):
        # Attempt access by a non-participant user
        self.client.login(username='user3', password='password123')
        response = self.client.get(reverse('chat_detail', kwargs={'pk': self.chat.id}))
        # Check if the response is forbidden
        self.assertEqual(response.status_code, 403)

    def test_correct_context_data(self):
        # Access by a valid participant
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('chat_detail', kwargs={'pk': self.chat.id}))
        # Check if the correct data is in the context
        self.assertEqual(response.status_code, 200)
        messages = list(response.context_data['messages'])
        self.assertIn(self.message1, messages)
        self.assertIn(self.message2, messages)


class SendMessageTestCase(TestCase):
    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='user1', password='testpassword123')
        self.user2 = User.objects.create_user(username='user2', password='testpassword123')
        # Create a chat instance
        self.chat = Chat.objects.create(participant_one=self.user1, participant_two=self.user2)
        # Log in user1 for the test
        self.client.login(username='user1', password='testpassword123')

    def test_send_message_success(self):
        url = reverse('send_message', kwargs={'chat_id': self.chat.id})
        response = self.client.post(url, {'message_text': 'Hello, this is a test message'})
        # Check redirection to chat detail page
        self.assertRedirects(response, reverse('chat_detail', kwargs={'pk': self.chat.id}))
        # Check that the message was added to the database
        message = Message.objects.first()
        self.assertIsNotNone(message)
        self.assertEqual(message.text, 'Hello, this is a test message')
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.chat, self.chat)

    def test_send_message_empty(self):
        url = reverse('send_message', kwargs={'chat_id': self.chat.id})
        response = self.client.post(url, {'message_text': ''})
        # Should still redirect back to the chat detail
        self.assertRedirects(response, reverse('chat_detail', kwargs={'pk': self.chat.id}))
        # No message should be added to the database
        message_count = Message.objects.count()
        self.assertEqual(message_count, 0)


class LikeItemTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.category = Category.objects.create(name="Books")
        self.item = Item.objects.create(name='Sample Item', description='Description here', category=self.category,
                                        owner=self.user)
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_like_item_success(self):
        url = reverse('like-item', kwargs={'item_id': self.item.id})
        response = self.client.post(url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Item liked successfully!')
        self.assertTrue(Like.objects.filter(item=self.item, liker=self.user).exists())

    def test_like_item_already_liked(self):
        Like.objects.create(item=self.item, liker=self.user)
        url = reverse('like-item', kwargs={'item_id': self.item.id})
        response = self.client.post(url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'You have already liked this item.')
        self.assertEqual(Like.objects.filter(item=self.item, liker=self.user).count(), 1)


class ChatDeleteTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='user1password')
        self.user2 = User.objects.create_user(username='user2', password='user2password')
        self.other_user = User.objects.create_user(username='other_user', password='otherpassword')
        self.chat = Chat.objects.create(participant_one=self.user1, participant_two=self.user2)

        self.client = Client()

    def test_delete_chat_unauthorized_user(self):
        # Log in as other_user who is not part of the chat.
        self.client.login(username='other_user', password='otherpassword')
        url = reverse('delete_chat', kwargs={'chat_id': self.chat.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('match_list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "You do not have permission to delete this chat.")
        self.assertTrue(Chat.objects.filter(pk=self.chat.pk).exists())

    def test_delete_chat_non_post_request(self):
        self.client.login(username='user1', password='user1password')
        url = reverse('delete_chat', kwargs={'chat_id': self.chat.pk})
        response = self.client.get(url)  # Attempt a GET request instead of POST
        # Expecting some kind of HTTP error like 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)


class UpdateLocationViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass',
            latitude=10.0, longitude=20.0,
            location=Point(20.0, 10.0)
        )
        self.client.login(username='testuser', password='testpass')
        self.url = reverse('update_location')

    def test_update_location_authenticated(self):
        response = self.client.post(self.url, json.dumps({
            'latitude': 30.0,
            'longitude': 40.0
        }), content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.latitude, 30.0)
        self.assertEqual(self.user.longitude, 40.0)
        self.assertEqual(self.user.location.x, 40.0)
        self.assertEqual(self.user.location.y, 30.0)

    def test_update_location_invalid_json(self):
        response = self.client.post(self.url, 'invalid-json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'success': False, 'error': 'Invalid JSON'})

    def test_update_location_invalid_latitude_longitude(self):
        response = self.client.post(self.url, json.dumps({
            'latitude': 'invalid',
            'longitude': 'invalid'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'success': False, 'error': 'Latitude and longitude must be numbers'})

        response = self.client.post(self.url, json.dumps({
            'latitude': 95.0,
            'longitude': 195.0
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'success': False, 'error': 'Latitude or longitude out of range'})

    def test_update_location_unauthenticated(self):
        self.client.logout()
        response = self.client.post(self.url, json.dumps({
            'latitude': 30.0,
            'longitude': 40.0
        }), content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_update_location_other_user(self):
        other_user = User.objects.create_user(
            username='otheruser', password='otherpass',
            latitude=50.0, longitude=60.0,
            location=Point(60.0, 50.0)
        )
        self.client.login(username='otheruser', password='otherpass')
        response = self.client.post(self.url, json.dumps({
            'latitude': 30.0,
            'longitude': 40.0
        }), content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        other_user.refresh_from_db()
        self.assertEqual(other_user.latitude, 30.0)
        self.assertEqual(other_user.longitude, 40.0)
        self.assertEqual(other_user.location.x, 40.0)
        self.assertEqual(other_user.location.y, 30.0)
