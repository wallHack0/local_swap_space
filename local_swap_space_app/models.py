from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.geos import Point
from django.contrib.gis.db import models as geomodels
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


# User model with city and geolocation parameters.
class User(AbstractUser):
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    latitude = models.FloatField(null=True, blank=True, verbose_name="latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="longitude")
    location = geomodels.PointField(geography=True, null=True, blank=True, verbose_name="location")

    def save(self, *args, **kwargs):
        # Custom save method to automatically update the 'location' field based on latitude and longitude.
        try:
            if self.latitude is not None and self.longitude is not None:
                # Ensures latitude and longitude are float before creating a Point.
                if isinstance(self.latitude, float) and isinstance(self.longitude, float):
                    self.location = Point(self.longitude, self.latitude, srid=4326)
                else:
                    raise ValidationError("Latitude and Longitude must be float.")
        except (ValueError, ValidationError) as e:
            # Logs error if there is an issue updating the location.
            logger.error(f'Error updating location for user {self.username}: {str(e)}')
            raise
        super().save(*args, **kwargs) # Calls the superclass' save method to handle the actual saving.


# Category model for items.
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Model representing an item.
class Item(models.Model):
    # Choices for item availability status.
    STATUS_CHOICES = [
        ('AVAILABLE', 'AVAILABLE'),
        ('RESERVED', 'RESERVED'),
    ]

    name = models.CharField(max_length=255)  
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # Foreign link to category of the item.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Foreign link to owner of the item.
    status = models.CharField(max_length=100, choices=STATUS_CHOICES,
                              default='AVAILABLE')

    def __str__(self):
        return f"{self.name} ({self.status})"


# Photos of the item.
class ItemImage(models.Model):
    item = models.ForeignKey(Item, related_name='images', on_delete=models.CASCADE)  # Link to the Item.
    image = models.ImageField(upload_to='item_images/')  # Path to store the image.

    def __str__(self):
        return f"Image for {self.item.name} (ID: {self.item.id})"


# Model representing a 'like' on an item.
class Like(models.Model):
    item = models.ForeignKey(Item, related_name='likes', on_delete=models.CASCADE)  # Item that is liked.
    liker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='given_likes',
                              on_delete=models.CASCADE)  # User who liked the item.
    liked_on = models.DateTimeField(auto_now_add=True)  # Timestamp of the like.

    def __str__(self):
        return f"{self.liker.username} liked {self.item.name}"


# Match model between two likes.
class Match(models.Model):
    # ForeignKey to the Like model for the first like involved in the match.
    like_one = models.ForeignKey(Like, related_name='matches_as_one',
                                 on_delete=models.CASCADE)
    # ForeignKey to the Like model for the second like involved in the match.
    like_two = models.ForeignKey(Like, related_name='matches_as_two',
                                 on_delete=models.CASCADE)
    matched_on = models.DateTimeField(auto_now_add=True)  # Timestamp of the match.

    class Meta:
        # Ensures that the combination of like_one and like_two is unique.
        # This prevents duplicate matches between the same pair of likes.
        unique_together = ('like_one', 'like_two')  # Uniqueness of the match.

    def __str__(self):
        return f"Match: {self.like_one.item.name} and {self.like_two.item.name}"


# Chat model between two users.
class Chat(models.Model):
    # ForeignKey to the User model for the first participant of the chat.
    participant_one = models.ForeignKey(User, on_delete=models.CASCADE,
                                        related_name="chats_as_participant_one")
    # ForeignKey to the User model for the second participant of the chat.
    participant_two = models.ForeignKey(User, on_delete=models.CASCADE,
                                        related_name="chats_as_participant_two")
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the chat was created.

    class Meta:
        # Ensures that the combination of participant_one and participant_two is unique.
        # Prevents the creation of duplicate chats between the same two users.
        unique_together = ('participant_one', 'participant_two')

    def __str__(self):
        return f"Chat between {self.participant_one} and {self.participant_two}"


# Model representing a message in a chat.
class Message(models.Model):
    # Foreign key to the Chat model, establishing a relationship where each message is linked to a specific chat.
    chat = models.ForeignKey(Chat, related_name='messages',
                             on_delete=models.CASCADE)
    # Foreign key to the AUTH_USER_MODEL, linking each message to its sender.
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()  # Content of the message.
    sent_at = models.DateTimeField(auto_now=True)  # Timestamp when the message was sent.

    def __str__(self):
        return f"Message from {self.sender.username} at {self.sent_at}"


# Model representing rating between users.
class Rating(models.Model):
    # ForeignKey linking to the user being rated.
    rated_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_ratings',
                                   on_delete=models.CASCADE)
    # ForeignKey linking to user who gives the rating.
    rating_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='given_ratings',
                                    on_delete=models.CASCADE)
    # A field to store the rating value. It accepts integers from 1 to 5.
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])

    class Meta:
        # Ensures that a user cannot rate another user more than once.
        unique_together = ('rated_user', 'rating_user')

    def __str__(self):
        return f"{self.rating_user.username} rates {self.rated_user.username} a {self.rating}"
