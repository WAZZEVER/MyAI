import { auth, db } from '/fireauth.js';
import {
    getAuth,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signOut,
    onAuthStateChanged,
  } from "https://www.gstatic.com/firebasejs/10.13.1/firebase-auth.js";
  import {
    getFirestore,
    collection,
    addDoc,
    getDocs,
    doc,
    setDoc,
    getDoc,
  } from "https://www.gstatic.com/firebasejs/10.13.1/firebase-firestore.js";

// Function to fetch and display reminders
export async function fetchAndDisplayReminders(user_id) {
  const reminderItems = document.getElementById("reminder_items");

  if (!reminderItems) {
    console.error('Element with ID "reminder_items" not found');
    return;
  }

  if (user_id) {
    try {
      const userRemindersRef = collection(db, "users", user_id, "reminders");
      const querySnapshot = await getDocs(userRemindersRef);
      reminderItems.innerHTML = ""; // Clear previous content

      querySnapshot.forEach((doc) => {
        const reminder = doc.data();
        const reminderItem = `
                  <div class="reminder-item">
                      <div>${reminder.time}</div>
                      <div>${reminder.reason}</div>
                      <div>${reminder.date}</div>
                  </div>
              `;
        reminderItems.innerHTML += reminderItem;
      });
    } catch (error) {
      console.error("Error fetching reminders:", error);
      reminderItems.innerHTML = "<p>Error: Unable to load reminders.</p>";
    }
  } else {
    reminderItems.innerHTML = "<p>Please log in to view reminders.</p>";
  }
}

// Event listeners for forms and authentication
document.addEventListener('DOMContentLoaded', () => {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const signinForm = document.getElementById('signin-form');
  const signupForm = document.getElementById('signup-form');


    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      });
    });


    signinForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = e.target.elements[0].value;
      const password = e.target.elements[1].value;
      console.log('Sign in:', email, password);
      signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
          const user = userCredential.user;
          console.log("User signed in:", user);
          window.location.href = '/app'; // Redirect after sign-in
        })
        .catch((error) => {
          console.error("Error signing in:", error);
          alert("Error signing in: " + error.message);
        });
    });

    signupForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = e.target.elements[0].value;
      const password = e.target.elements[1].value;
      const confirmPassword = e.target.elements[2].value;
      console.log('Sign up:', email, password, confirmPassword);
      if (password === confirmPassword) {
        createUserWithEmailAndPassword(auth, email, password)
          .then((userCredential) => {
            const user = userCredential.user;
            console.log("User created:", user);
            window.location.href = '/app'; // Redirect after signup
          })
          .catch((error) => {
            console.error("Error signing up:", error);
            alert("Error creating account: " + error.message);
          });
      } else {
        alert("Passwords do not match.");
      }
    });

    onAuthStateChanged(auth, async (user) => {
      if (user) {

        const userUID = user.uid;

        // Dispatch a custom event when the UID is ready
        const event = new CustomEvent("userUIDReady", {
          detail: { userUID: userUID },
        });
        document.dispatchEvent(event); // Dispatch event to the DOM

        const userDocRef = doc(db, "users", user.uid);
        const userDoc = await getDoc(userDocRef);

        if (!userDoc.exists()) {
          await setDoc(userDocRef, {
            email: user.email,
            createdAt: new Date(),
          });
          console.log("User document created");
        }
        window.location.href = '/app'; // Redirect after sign-in
        // fetchAndDisplayReminders(user.uid); // Fetch and display reminders when user is authenticated
      } else {
      }
    });
});
