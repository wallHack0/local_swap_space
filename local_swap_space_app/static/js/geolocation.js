// Listening for the 'submit' event on the registration form.
document.getElementById('registrationForm').addEventListener('submit', function (event) {
    // Checking if geolocation is available in the browser.
    if (navigator.geolocation) {
        // Preventing the default form submission behavior to first obtain geolocation.
        event.preventDefault();

        // Attempting to get the current geographic position of the user.
        navigator.geolocation.getCurrentPosition(function (position) {
            let latitude = position.coords.latitude;
            let longitude = position.coords.longitude;

            // Creating hidden inputs to store latitude and longitude.
            let hiddenLat = document.createElement('input');
            hiddenLat.setAttribute('type', 'hidden');
            hiddenLat.setAttribute('name', 'latitude');
            hiddenLat.value = latitude;
            // Appending the hidden input to the form.
            document.getElementById('registrationForm').appendChild(hiddenLat);

            let hiddenLong = document.createElement('input');
            hiddenLong.setAttribute('type', 'hidden');
            hiddenLong.setAttribute('name', 'longitude');
            hiddenLong.value = longitude;
            document.getElementById('registrationForm').appendChild(hiddenLong);

            // Submitting the form again after adding the hidden inputs.
            document.getElementById('registrationForm').submit();

        }, function (error) {
            console.log("Błąd: ", error);
            // Submitting the form even if there's an error while obtaining geolocation.
            document.getElementById('registrationForm').submit();
        });
    }
});
