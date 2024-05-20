from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic.edit import FormView, UpdateView
from django.views.generic import ListView, TemplateView, DetailView
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.contrib import messages
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Avg, Prefetch
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponseRedirect
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ItemForm, RatingForm, ItemImageForm, \
    CustomUserChangeForm
from .models import Item, Category, User, Like, Match, Chat, Message, Rating, ItemImage


class RegisterView(FormView):
    """
    RegisterView handles user registration through a form interface using CustomUserCreationForm.
    The view renders a registration page, processes valid form submissions by saving user data
    (including optional geolocation fields), automatically logs in the new user, and redirects
    to a success URL ('dashboard').

    Attributes:
        template_name (str): The template name used to render the registration page.
        form_class (CustomUserCreationForm): The form class used for user registration.
        success_url (str): The URL to redirect to upon successful form submission.
    """
    template_name = 'register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        """
        Processes the valid form submission.

        Saves the form data to create a new user instance, sets additional user attributes,
        handles optional geolocation data, logs the new user in, and redirects to the success URL.

        Args:
            form (CustomUserCreationForm): The form instance containing cleaned data.

        Returns:
            HttpResponseRedirect: Redirects to the success URL specified in success_url.
        """
        # Save the form data to create a new user instance, but do not commit to the database yet.
        user = form.save(commit=False)

        # Extract and set additional user attributes directly from the cleaned form data.
        user.city = form.cleaned_data.get('city')

        # Convert latitude and longitude from the form to float if they are not None.
        latitude = form.cleaned_data.get('latitude')
        longitude = form.cleaned_data.get('longitude')

        try:
            if latitude is not None and longitude is not None:
                user.latitude = float(latitude)
                user.longitude = float(longitude)
        except ValueError:
            # Later will hand the error in better way.
            print("Incorrect latitude and longitude data.")

        # Save the user object to the database.
        user.save()

        # Log the user in automatically after registering.
        login(self.request, user)

        # Call the parent class's form_valid method to handle redirection to success_url.
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    CustomLoginView modifies the standard Django login process by using a custom authentication form.
    Beyond the standard user credential validation, this view also handles the storage of geolocation data
    (latitude and longitude) if the user has allowed access to their location in the browser.
    After successful login and optional geolocation data update, the user is redirected to the dashboard page.

    Attributes:
        template_name (str): The template name used to render the login page.
        form_class (CustomAuthenticationForm): The form class used for user authentication.
    """
    template_name = 'login.html'
    form_class = CustomAuthenticationForm

    def form_valid(self, form):
        """
        Processes the valid form submission.

        Logs in the user, updates optional geolocation data if provided, and redirects to the success URL.

        Args:
            form (CustomAuthenticationForm): The form instance containing cleaned data.

        Returns:
            HttpResponseRedirect: Redirects to the success URL specified in get_success_url.
        """
        login(self.request, form.get_user())

        latitude = form.cleaned_data.get('latitude')
        longitude = form.cleaned_data.get('longitude')

        try:
            if latitude and longitude:
                latitude = float(latitude)
                longitude = float(longitude)
                user = form.get_user()
                user.latitude = latitude
                user.longitude = longitude
                user.save()
        except ValueError:
            print("Wrong values for latitude and longitude.")

        return super().form_valid(form)

    def get_success_url(self):
        """
        Determines the URL to redirect to after successful login.

        Returns:
            str: The URL to redirect to after a successful login, which is the 'dashboard' page.
        """
        return reverse_lazy('dashboard')


class DashboardView(LoginRequiredMixin, ListView):
    """
    DashboardView inherits from Django's LoginRequiredMixin to ensure that only authenticated users have access, and
    from ListView for streamlined display of items. This view enhances item listing by filtering items based on
    categories and proximity to the user's location.

    Attributes:
        model (Item): The model that this view will be displaying.
        template_name (str): The template name used to render the dashboard page.
        context_object_name (str): The name of the context object that will be used in the template.
    """
    model = Item
    template_name = 'dashboard.html'
    context_object_name = 'items'

    def get_queryset(self):
        """
        Retrieves the queryset of items to be displayed on the dashboard.

        Filters the items based on the category and proximity to the user's location. Excludes items
        owned by the logged-in user. If 'reset' is in the GET parameters, the filters for distance and
        category are removed.

        Returns:
            QuerySet: The filtered and ordered queryset of items.
        """
        # Retrieve the base queryset with related models.
        items = super().get_queryset().select_related('category', 'owner').prefetch_related('images')
        # Exclude items owned by the logged-in user.
        items = items.exclude(owner=self.request.user)

        user_location = self.request.user.location  # Location of the logged-in user.
        max_distance = self.request.GET.get('distance', None)  # Maximum distance fetched from GET parameters.
        category_id = self.request.GET.get('category')  # Category ID fetched from GET parameters.

        if 'reset' in self.request.GET:
            # If reset is activated, remove filters for distance and category.
            max_distance = None
            category_id = None

        if category_id:
            # Filter items by category if a category has been selected.
            items = items.filter(category__id=category_id)

        if user_location:
            # Annotate each item with the distance from the user if location is available.
            items = items.annotate(distance=Distance('owner__location', user_location))
            if max_distance:
                # If a maximum distance is specified, filter items that are within this range.
                max_distance = float(max_distance)
                items = items.filter(distance__lte=D(km=max_distance))
            # Order items by distance and name.
            items = items.order_by('distance', 'name')
        else:
            pass

        return items

    def get_context_data(self, **kwargs):
        """
        Adds extra context to the template.

        Adds all categories to the context so they can be used for filtering in the template.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: The context data for the template.
        """
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemDetailView(LoginRequiredMixin, DetailView):
    """
    ItemDetailView provides a detailed view of a specific item, accessible only to authenticated users.
    Built on Django's DetailView, it displays detailed information about an item identified by its URL ID.
    The view extends DetailView's functionality by adding a list of item images to the context.

    Attributes:
        model (Item): The model that this view will be displaying.
        template_name (str): The template name used to render the item detail page.
        context_object_name (str): The name of the context object that will be used in the template.
    """
    model = Item
    template_name = 'item_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        """
        Adds extra context to the template.

        Retrieves all images associated with the item and adds them to the context.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: The context data for the template, including item images.
        """
        context = super().get_context_data(**kwargs)
        item_images = ItemImage.objects.filter(item=self.object)  # Retrieve all associated images.
        context['item_images'] = item_images
        return context


class AddItemView(LoginRequiredMixin, View):
    """
    AddItemView handles the process of adding a new item to the system. This view is restricted to authenticated users
    by utilizing the LoginRequiredMixin. The view supports both GET and POST requests to display forms and process
    data submissions, respectively.

    This view utilizes two distinct forms: one for the item details and another for uploading item images, enabling
    users to input all necessary information and upload images during the item creation process.
    """

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests.

        Displays the form for adding a new item and uploading images.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The rendered 'add_item.html' template with the item and image forms.
        """
        item_form = ItemForm(editable_name=True)  # The 'name' field is editable.
        image_form = ItemImageForm()
        return render(request, 'add_item.html', {'item_form': item_form, 'image_form': image_form})

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests.

        Processes the form submission for adding a new item and uploading images. If the forms are valid, the new item
        and associated image are saved to the database. If the forms are not valid, the forms are re-rendered with
        error messages.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseRedirect: Redirects to the item's detail page upon successful form submission.
            HttpResponse: The rendered 'add_item.html' template with the item and image forms if validation fails.
        """
        item_form = ItemForm(request.POST, editable_name=True)
        image_form = ItemImageForm(request.POST, request.FILES)
        if item_form.is_valid() and image_form.is_valid():
            new_item = item_form.save(commit=False)
            new_item.owner = request.user  # Assign the item's owner as the current user.
            new_item.save()
            new_image = image_form.save(commit=False)
            new_image.item = new_item  # Associate the new image with the newly created item.
            new_image.save()
            return redirect(reverse('item-detail', kwargs={'pk': new_item.pk}))
        return render(request, 'add_item.html',
                      {'item_form': item_form, 'image_form': image_form})  # Re-render the form if validation fails


class ItemUpdateView(LoginRequiredMixin, UpdateView):
    """
    ItemUpdateView handles the process of updating an existing item. It ensures that only authenticated users can update
    items using LoginRequiredMixin. This view utilizes Django's built-in UpdateView for handling form submissions.

    Attributes:
        model (Item): The model that this view will be updating.
        form_class (ItemForm): The form class used to update the item.
        template_name (str): The template name used to render the edit item page.
        context_object_name (str): The name of the context object that will be used in the template.
    """
    model = Item
    form_class = ItemForm
    template_name = 'edit_item.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        """
        Extends the base implementation to add item images to the context, allowing them to be displayed and potentially
        updated along with other item details.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for the template, including item images.
        """
        context = super().get_context_data(**kwargs)
        context['item_images'] = ItemImage.objects.filter(item=self.object)  # Add associated images to the context.
        return context

    def get_form_kwargs(self):
        """
        Extends the base implementation to modify the form kwargs based on view-specific requirements. Here, it sets
        'editable_name' to 'False' to prevent editing the item's name.

        Returns:
            dict: The keyword arguments for instantiating the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs['editable_name'] = False  # Disallow editing of the item's name through the form.
        return kwargs

    def get_success_url(self):
        """
        Determines the URL to redirect to after a successful form submission.

        Returns:
            str: The URL to redirect to after a successful item update, which is the item's detail page.
        """
        return reverse_lazy('item-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """
        Extends the base method to add a success message after the item is successfully updated.

        Args:
            form (ItemForm): The form instance containing cleaned data.

        Returns:
            HttpResponseRedirect: Redirects to the success URL specified in get_success_url.
        """
        messages.success(self.request, "Item has been succesfully updated!")
        return super().form_valid(form)


class AddImageView(LoginRequiredMixin, View):
    """
    AddImageView handles image uploads for a specific item. This view ensures that only authenticated users can
    add images. This view directly handles POST requests to upload images. If the image is successfully uploaded,
    the user is redirected back to the item edit page with a success message. If no image is provided, an error message
    is shown.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for uploading images to a specific item.

        Retrieves the item based on the primary key provided in the URL. If an image file is included in the request,
        it creates a new ItemImage instance and associates it with the item. On successful upload, the user is redirected
        back to the item edit page with a success message. If no image is provided, an error message is shown and the user
        is redirected back to the item edit page.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments containing the primary key of the item.

        Returns:
            HttpResponseRedirect: Redirects to the item edit page with a success or error message.
        """
        item = Item.objects.get(pk=kwargs['pk'])
        if 'image' in request.FILES:
            new_image = ItemImage(item=item, image=request.FILES['image'])  # Create a new ItemImage instance.
            new_image.save()
            messages.success(request, "Image added successfully!")
            return redirect('edit_item', pk=item.pk)
        else:
            messages.error(request, "You must provide an image file.")  # Add an error message.
            return redirect('edit_item', pk=item.pk)


class DeleteImageView(LoginRequiredMixin, View):
    """
    DeleteImageView handles the deletion of a specific image associated with an item. This view ensures that only
    authenticated users can delete images.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for deleting a specific image associated with an item.

        Retrieves the image based on the primary key provided in the URL. Deletes the image from the database, and
        redirects the user back to the item edit page with a success message.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments containing the primary key of the image to be deleted.

        Returns:
            HttpResponseRedirect: Redirects to the item edit page with a success message.
        """
        image = ItemImage.objects.get(pk=kwargs['pk'])  # Getting an image.
        item_pk = image.item.pk
        image.delete()
        messages.success(request, "Image deleted successfully!")  # Add a success message.
        return redirect('edit_item', pk=item_pk)


class DeleteItemView(LoginRequiredMixin, View):
    """
    DeleteItemView allows a logged-in user to delete an item they own. If the item is part of a match,
    informs the user about the match and prompts them to delete the match before deleting the item.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to delete a specific item owned by the user.

        Retrieves the item based on the primary key provided in the URL. Checks if the user owns the item,
        and if the item is part of any match. If the item is part of a match, a warning message is shown and
        the user is redirected back to the item detail page. If the user does not own the item, an error message
        is shown. If the item can be deleted, all associated images are deleted first, followed by the item itself.
        A success message is then shown, and the user is redirected to the dashboard.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments containing the primary key of the item to be deleted.

        Returns:
            HttpResponseRedirect: Redirects to the item detail page with a warning message if the item is part of a match.
            HttpResponseRedirect: Redirects to the item detail page with an error message if the user does not own the item.
            HttpResponseRedirect: Redirects to the dashboard with a success message if the item is successfully deleted.
        """
        item_id = kwargs.get('item_id')
        item = get_object_or_404(Item, pk=item_id)

        # Check if the user owns the item.
        if item.owner != request.user:
            messages.error(request, "You do not have permission to delete this item.")
            return HttpResponseRedirect(reverse('item-detail', kwargs={'pk': item_id}))

        with transaction.atomic():
            # Check if the item is part of any match.
            if Match.objects.filter(like_one__item=item).exists() or Match.objects.filter(like_two__item=item).exists():
                messages.warning(request,
                                 "This item is part of a match. Please delete the match before deleting the item.")
                return HttpResponseRedirect(reverse('item-detail', kwargs={'pk': item_id}))

            # Delete all images associated with the item.
            item.images.all().delete()

            # Delete the item itself.
            item.delete()

            messages.success(request, "Item and associated images deleted successfully.")
            return HttpResponseRedirect(reverse('dashboard'))


class UserProfileView(LoginRequiredMixin, TemplateView):
    """
    UserProfileView provides a detailed profile page for a user. This view is only accessible to authenticated users.
    It displays detailed information about the user, including their listed items and
    average rating received from other users.

    Attributes:
        template_name (str): The template name used to render the user profile page.
    """
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        """
        Retrieves the necessary data to populate the user profile page.

        Fetches the current user from the request and adds it to the context. Retrieves the items listed by the user
        and adds them to the context. Calculates the average rating received by the user and adds it to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user  # Fetch the user from the request.
        context['profile_user'] = user  # Add the user to the context.
        context['items'] = Item.objects.filter(owner=user).prefetch_related('images')  # User's items.

        # Calculate the average rating for the user and handle the case if there are no ratings.
        average_rating = Rating.objects.filter(rated_user=user).aggregate(Avg('rating'))['rating__avg']
        context['average_rating'] = average_rating if average_rating is not None else "No ratings"
        return context


class EditUserProfileView(LoginRequiredMixin, UpdateView):
    """
    UserProfileEditView allows authenticated users to edit their profile information.

    Attributes:
        model (User): The user model used for the form.
        form_class (CustomUserChangeForm): The form class used for updating user profile information.
        template_name (str): The template name used to render the edit profile page.
        success_url (str): The URL to redirect to after a successful form submission.
    """
    model = User
    form_class = CustomUserChangeForm
    template_name = 'edit_profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, **kwargs):
        """
        Overrides the get_object method to return the currently authenticated user.

        Returns:
            User: The currently authenticated user.
        """
        return self.request.user


class OtherUserProfileView(LoginRequiredMixin, DetailView):
    """
    OtherUserProfileView displays a detailed profile page for a specific user, identified by their username.
    This view is also secured with LoginRequiredMixin to ensure that only authenticated users can view profiles.
    It allows the current user to view other users' profiles including items they own, their average rating,
    and potentially rate them if certain conditions are met.

    Attributes:
        model (Model): Django model to query for this view, here it is User.
        template_name (str): Path to the HTML template used for rendering the profile.
        context_object_name (str): Name of the context variable used in the template to represent the User object.
        slug_field (str): Model field that corresponds to the URL capture value to filter the User object.
        slug_url_kwarg (str): Name of the keyword argument that captures the value from the URL.
    """
    model = User
    template_name = 'other_user_profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        """
        Extends the base implementation to include items owned by the user, check for existing ratings,
        determine if the current user can rate the profile user, and include a form for rating if applicable.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        other_user = context['profile_user']
        user = self.request.user

        # Include items owned by the user being viewed.
        context['items'] = Item.objects.filter(owner=other_user)

        # Include existing rating if any.
        existing_rating = Rating.objects.filter(rated_user=other_user, rating_user=user).first()
        context['existing_rating'] = existing_rating.rating if existing_rating else None

        # Determine if the current user can rate the profile user based on mutual likes.
        context['can_rate'] = Match.objects.filter(
            Q(like_one__liker=user, like_two__liker=other_user) |
            Q(like_one__liker=other_user, like_two__liker=user)
        ).exists()

        if context['can_rate']:
            context['rating_form'] = RatingForm()

        # Calculate and include the average rating for the profile user.
        average_rating = Rating.objects.filter(rated_user=other_user).aggregate(Avg('rating'))['rating__avg']
        context['average_rating'] = average_rating if average_rating is not None else "No ratings"

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to rate the profile user. Validates the form and updates or creates the rating.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseRedirect: Redirects to the other user profile page with a success message upon successful rating submission.
            HttpResponseRedirect: Redirects to the other user profile page with an error message if there was an error with the submission.
        """
        self.object = self.get_object()  # Retrieve the user object from the URL.
        context = self.get_context_data(object=self.object)

        # Return GET view if the user is not allowed to rate.
        if not context['can_rate']:
            return self.get(request, *args, **kwargs)

        form = RatingForm(request.POST)
        if form.is_valid():
            Rating.objects.update_or_create(
                rated_user=self.object,
                rating_user=request.user,
                defaults={'rating': form.cleaned_data['rating']}
            )
            messages.success(request, "Your rating has been submitted.")
            return redirect('other-user-profile', username=self.object.username)

        messages.error(request, "There was an error with your submission.")
        return self.get(request, *args, **kwargs)


class LikedItemsView(LoginRequiredMixin, ListView):
    """
    LikedItemsView displays a list of items that the currently logged-in user has liked.
    This view leverages LoginRequiredMixin to ensure only authenticated users can access the list of liked items.
    The view uses Django's ListView for displaying a list based on a Django model.

    Attributes:
        model (Model): Django model to query for this view, here it is Like.
        template_name (str): Path to the HTML template used for rendering the liked items list.
        context_object_name (str): Name of the context variable used in the template to represent the list of likes.
    """
    model = Like
    template_name = 'liked_items.html'
    context_object_name = 'likes'

    def get_queryset(self):
        """
        Retrieves the queryset of liked items by the currently logged-in user.

        Returns:
            queryset: Queryset of liked items by the currently logged-in user, ordered by most recent.
        """
        # Retrieves likes by the logged-in user, ordered by most recent.
        return Like.objects.filter(liker=self.request.user).prefetch_related(
            Prefetch('item__images', queryset=ItemImage.objects.order_by('id'))  # Ensures images are prefetched.
        ).order_by('-liked_on')

    def get_context_data(self, **kwargs):
        """
        Retrieves additional context data for the liked items list view.

        Adds items owned by the logged-in user that have received likes to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        # Add items owned by the logged-in user that have received likes.
        context['my_items'] = Item.objects.filter(owner=self.request.user).prefetch_related('likes')
        return context


class MatchUserListView(LoginRequiredMixin, ListView):
    """
    MatchUserListView displays a list of matched users based on mutual likes between items.
    It inherits from ListView and requires user authentication provided by LoginRequiredMixin.
    This view is specifically designed to manage and display user matches which could potentially lead to further
    message sending.

    Attributes:
        model (Model): Django model to query for this view, here it is Match.
        template_name (str): Path to the HTML template used for rendering the matched user list.
        context_object_name (str): Name of the context variable used in the template to represent the list of matches.
    """

    model = Match
    template_name = 'match_user_list.html'
    context_object_name = 'matches'

    def get_queryset(self):
        """
        Retrieves the queryset of matches involving the current user and prepares them for rendering.

        Overrides the default queryset to retrieve matches that involve the current user either as like_one or like_two
        participant in the match. It then groups these matches by the other participant to simplify the rendering
        logic in the template. The grouping process also involves creation of a chat session for each
        unique pair of matched users if it does not already exist.

        Returns:
            list: List of dictionaries representing the matches and related data for rendering in the template.
        """
        user = self.request.user
        # Retrieve all matches where the current user is either like_one or like_two participant.
        # The 'distinct()' ensures that each match is unique, avoiding duplicates in the list.
        matches = Match.objects.filter(
            Q(like_one__liker=user) | Q(like_two__liker=user)
        ).distinct()

        # Dictionary to group matches by other user, including sets for items and chat session info.
        grouped_matches = defaultdict(lambda: {'items_from_user': set(), 'items_from_them': set(), 'chat': None})

        for match in matches:
            # Identify the other participant in the match.
            other_user = match.like_two.liker if match.like_one.liker == user else match.like_one.liker

            # Identify which item was liked by the current user and the other user.
            item_from_user = match.like_one.item if match.like_one.liker == user else match.like_two.item
            item_from_them = match.like_two.item if match.like_one.liker == user else match.like_one.item

            # Create a unique pair key based on user IDs to prevent duplicate chat sessions.
            user_pair_key = (min(user.id, other_user.id), max(user.id, other_user.id))

            # Check if a chat session exists for this user pair; create one if it doesn't exist.
            if grouped_matches[other_user]['chat'] is None:
                grouped_matches[other_user]['chat'], _ = Chat.objects.get_or_create(
                    participant_one=User.objects.get(id=user_pair_key[0]),
                    participant_two=User.objects.get(id=user_pair_key[1])
                )

            # Add items to the respective sets in the grouped data structure.
            grouped_matches[other_user]['items_from_user'].add(item_from_user)
            grouped_matches[other_user]['items_from_them'].add(item_from_them)

        # Return a list of dictionaries for easier template rendering.
        # each dictionary represents a unique match with combined info.
        return [{'other_user': key, **value} for key, value in grouped_matches.items()]


class ChatView(LoginRequiredMixin, DetailView):
    """
    Provides a detailed view for a specific chat session. This view ensures that only participants of the chat
    can view its details and messages, securing privacy and relevancy to the involved users.

    Attributes:
        model (Model): Django model to query for this view, here it is Chat.
        context_object_name (str): Name of the context variable used in the template to represent the chat object.
        template_name (str): Path to the HTML template used for rendering the chat details.
    """
    model = Chat
    context_object_name = 'chat'
    template_name = 'chat_detail.html'

    def get_object(self, *args, **kwargs):
        """
        Retrieves the chat object based on the primary key provided in the URL and checks user participation.

        Overrides the base implementation to ensure that only participants of the chat can view its details and messages.

        Returns:
            Chat: The chat object if the logged-in user is a participant, else raises PermissionDenied.
        """
        # Retrieve the default chat object based on the primary key provided in the URL.
        chat = super().get_object(*args, **kwargs)
        user = self.request.user

        # Checks if the logged-in user is one of the participants in the chat.
        # If not, it denies access by returning an HttpResponseForbidden.
        if chat.participant_one != user and chat.participant_two != user:
            raise PermissionDenied("You are not allowed to view this chat.")

        return chat

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and ensures user participation in the chat.

        Returns:
            HttpResponse: The response with chat details and messages or Forbidden if user is not a participant.
        """
        self.object = self.get_object()

        # If the object is HttpResponseForbidden, return it directly.
        if isinstance(self.object, HttpResponseForbidden):
            return self.object

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        """
        Retrieves additional context data for the chat view, including associated messages.

        Returns:
            dict: The context data for rendering the template.
        """
        context = super().get_context_data(**kwargs)
        chat = context['chat']
        # Fetch all messages associated with this chat, ordered by the time they were sent.
        messages = chat.messages.all().order_by('sent_at')
        context['messages'] = messages

        return context


@login_required  # Ensures that only authenticated users can send messages.
@require_POST  # Ensures that this view only responds to POST requests.
def send_message(request, chat_id):
    """
    Handles the posting of a message to a specific chat identified by chat_id.

    This function checks if the user is authenticated and that the request is a POST.
    If the message text is not empty, it creates a new message associated with the chat.

    Args:
        request (HttpRequest): The HTTP request object.
        chat_id (int): The ID of the chat to which the message is being sent.

    Returns:
        HttpResponseRedirect: Redirects the user to the chat detail page after sending the message.
    """
    # Retrieve the chat object; return 404 if not found.
    chat = get_object_or_404(Chat, id=chat_id)

    # Extract message text from the POST request.
    message_text = request.POST.get('message_text')

    # Check if the message text is not empty.
    if message_text:
        Message.objects.create(chat=chat, sender=request.user, text=message_text)
        messages.success(request, "Message sent successfully.")

    return redirect('chat_detail', pk=chat_id)


@login_required  # Ensures that only logged-in users can perform the action.
@require_POST  # Restricts this function to handle only POST requests to ensure data is submitted securely.
def like_item(request, item_id):
    """
    Allows a user to like an item.

    The function ensures that each like is unique per user and item.
    If a user tries to like an item they have already liked, the function will not create a duplicate like.

    Args:
        request (HttpRequest): The HTTP request object.
        item_id (int): The ID of the item to be liked.

    Returns:
        HttpResponseRedirect: Redirects the user to the dashboard after liking the item.
    """
    # Retrieve the item by ID, returning a 404 error if not found.
    item = get_object_or_404(Item, pk=item_id)

    # Get the currently logged-in user from the request.
    user = request.user

    # Ensure the process is atomic to avoid issues with concurrent database access.
    with transaction.atomic():
        # Attempt to create a like, or get the existing like if it already exists.
        new_like, created = Like.objects.get_or_create(item=item, liker=user)

        if created:
            messages.success(request, "Item liked successfully!")
        else:
            messages.info(request, "You have already liked this item.")

    return redirect('dashboard')


@login_required  # Ensures that only logged-in users can access this function.
@require_POST  # Ensures this function can only be accessed through POST method to prevent CSRF attacks.
def delete_chat_and_related_data(request, chat_id):
    """
    Deletes a specific chat and all related data, including messages, likes, and matches,
    ensuring that the user has the right to delete the chat.

    Args:
        request (HttpRequest): The HTTP request object.
        chat_id (int): The ID of the chat to be deleted.

    Returns:
        HttpResponseRedirect: Redirects the user to the match list page after successfully deleting the chat.
    """
    # Retrieves the chat object; returns a 404 error if not found.
    chat = get_object_or_404(Chat, pk=chat_id)

    # Check if the current user is a participant of the chat.
    if request.user not in [chat.participant_one, chat.participant_two]:
        messages.error(request, "You do not have permission to delete this chat.")
        return redirect('match_list')

    # Begin an atomic transaction to ensure data integrity.
    with transaction.atomic():
        chat.messages.all().delete()

        # Find all likes associated with each participant in the chat.
        likes_from_participant_one = Like.objects.filter(liker=chat.participant_one)
        likes_from_participant_two = Like.objects.filter(liker=chat.participant_two)

        # Identify matches that should be deleted where either participant liked the other's item.
        matches_to_delete = Match.objects.filter(
            Q(like_one__in=likes_from_participant_one, like_two__in=likes_from_participant_two) |
            Q(like_one__in=likes_from_participant_two, like_two__in=likes_from_participant_one)
        )

        # Delete the identified matches and their associated likes.
        for match in matches_to_delete:
            likes_to_delete = [match.like_one, match.like_two]
            Like.objects.filter(id__in=[like.id for like in likes_to_delete]).delete()
            match.delete()

        # Delete the chat itself.
        chat.delete()

        messages.success(request, "Chat and all related data have been successfully deleted.")
        return redirect('match_list')
