Local Swap Space



Overview

Local Swap Space is a Django-based web application that facilitates local item exchange among users. Upon logging in, users gain access to a dashboard displaying items listed by other users. The application leverages Geolocation API and JavaScript to display items nearest to the user's location. Upon mutual interest in each other's items, users unlock access to a chat feature, encouraging face-to-face exchanges. Users can add, delete, and manage their listed items, rate other users, and view a list of matched items. The project utilizes PostgreSQL as its database backend.



Features

Dashboard: Provides a centralized view of items listed by other users, utilizing Geolocation API to display items nearest to the user's location.

Item Management: Users can add, edit, and delete their listed items.

Chat Functionality: Upon mutual interest in each other's items, users can unlock access to a chat feature for coordinating exchanges.

User Ratings: Users can rate each other based on their exchange experiences.

Matched Items List: Displays a list of items where mutual interest has been established between users.

Geolocation Integration: Utilizes Geolocation API and JavaScript to enhance user experience by displaying items based on proximity.



Installation
To set up the Local Swap Space project locally:

Clone the repository.
Set up and activate a virtual environment.
Install Django: pip install django.
Install PostgreSQL and set up a database.
Install additional dependencies: pip install -r requirements.txt.
Run migrations: python manage.py migrate.
Start the development server: python manage.py runserver.
Navigate to http://127.0.0.1:8000/ in your web browser to access the application.
Feedback and Contributions
Feedback, suggestions, and contributions are welcome! Feel free to use this project for your own purposes and customize it as needed.

