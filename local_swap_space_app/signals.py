from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Like, Match, Chat
from django.db.models import Q


@receiver(post_save, sender=Like)
def create_match_and_check_chat(sender, instance, created, **kwargs):
    """
    Signal handler that triggers after a Like instance is saved.
    It checks if there is a reciprocal like between the users involved and creates a match and chat if necessary.

    Parameters:
    - sender: The model class that sent the signal (Like).
    - instance: The actual instance of Like that was saved.
    - created: Boolean flag indicating whether a new record was created.
    - **kwargs: Additional keyword arguments.
    """
    if created:  # Checks if a new Like instance was created, not just updated.
        # Queries for potential reciprocal likes where the current liker is liked by the item owner.
        potential_likes = Like.objects.filter(item__owner=instance.liker, liker=instance.item.owner)
        for like in potential_likes:
            # Check if a Match does not already exist for the two likes in either direction.
            if not Match.objects.filter(
                    Q(like_one=instance, like_two=like) | Q(like_one=like, like_two=instance)).exists():
                # If not, create a new Match.
                new_match = Match.objects.create(like_one=instance, like_two=like)
                # Ensure consistent order for participants (lower ID first)
                user_one, user_two = sorted([instance.liker, like.liker], key=lambda user: user.id)
                # Get or create a chat between these users, ensuring only one chat exists per pair.
                Chat.objects.get_or_create(participant_one=user_one, participant_two=user_two)
