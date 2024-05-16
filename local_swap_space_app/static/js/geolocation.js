// Nasłuchiwanie na zdarzenie 'submit' w formularzu rejestracji.
document.getElementById('registrationForm').addEventListener('submit', function (event) {
    // Sprawdzenie, czy w przeglądarce dostępna jest geolokalizacja.
    if (navigator.geolocation) {
        // Zapobieganie domyślnemu zachowaniu wysyłania formularza, aby najpierw uzyskać geolokalizację.
        event.preventDefault();

        // Próba pobrania aktualnej pozycji geograficznej użytkownika.
        navigator.geolocation.getCurrentPosition(function (position) {
            let latitude = position.coords.latitude;
            let longitude = position.coords.longitude;

            // Tworzenie ukrytch inputów do przechowywania szerokości i długości geograficznej.
            let hiddenLat = document.createElement('input');
            hiddenLat.setAttribute('type', 'hidden');
            hiddenLat.setAttribute('name', 'latitude');
            hiddenLat.value = latitude;
            // Dołączanie ukrytego inputu do formularza.
            document.getElementById('registrationForm').appendChild(hiddenLat);

            let hiddenLong = document.createElement('input');
            hiddenLong.setAttribute('type', 'hidden');
            hiddenLong.setAttribute('name', 'longitude');
            hiddenLong.value = longitude;
            document.getElementById('registrationForm').appendChild(hiddenLong);

            // Ponowne wysłanie formularza po dodaniu ukrytych inputów.
            document.getElementById('registrationForm').submit();

        }, function (error) {
            console.log("Błąd: ", error);
            // Wysłanie formularza nawet w przypadku błędu podczas pobierania geolokalizacji.
            document.getElementById('registrationForm').submit();
        });
    }
});
