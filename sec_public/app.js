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
  deleteDoc,
} from "https://www.gstatic.com/firebasejs/10.13.1/firebase-firestore.js";

// Function to fetch and display reminders
export async function fetchAndDisplayReminders(user_id) {
  const reminderItems = document.getElementById("remindersList");

  if (!reminderItems) {
    console.error('Element with ID "remindersList" not found');
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
            <div class="reminder-details">
            <div class="reminder-time">${reminder.time}</div>
            <div class="reminder-reason">${reminder.reason}</div>
            <div class="reminder-date">${reminder.date}</div>
            <button class="delete-btn" data-id="${doc.id}">Delete</button>
            </div>
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
  const signOutButton = document.getElementById("signout-button");

  if (signOutButton) {
    signOutButton.addEventListener('click', () => {
      signOut(auth)
        .then(() => {
          console.log("User signed out.");
          window.location.href = "/"; // Redirect to home or login page
        })
        .catch((error) => {
          console.error("Error signing out:", error);
        });
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

        // Fetch and display reminders when user is authenticated
        fetchAndDisplayReminders(user.uid);
      } else {
        document.getElementById("remindersList").innerHTML =
          "<p>Please log in to view reminders.</p>";
        window.location.href = '/'; // Redirect after sign-in
      }
    });
  } else {
    console.error("Some of the required elements are missing.");
  }
});

let userUID = ""; // Define userUID at the top level for access in other functions

// New elements
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const chatMessages = document.getElementById('chatMessages'); // Container for chat messages

// Listen for the custom event from fireauth.js when the user UID is ready
document.addEventListener("userUIDReady", (event) => {
  userUID = event.detail.userUID; // Set the userUID variable when it's ready
  fetchAndDisplayReminders(userUID); // Fetch and display reminders when user UID is ready
});

// Function to display a chat message
function addMessage(text, sender) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `${sender}-message`);
  messageElement.textContent = text;
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
}

// Function to animate bot response
function animateResponse(element, text) {
  let index = 0;
  const speed = 50; // Speed of animation in milliseconds

  function type() {
    if (index < text.length) {
      element.textContent += text.charAt(index);
      index++;
      setTimeout(type, speed);
    }
  }

  type();
}

// Event listener for form submission
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault(); // Prevent default form submission (refresh)
  const message = messageInput.value.trim();
  if (message) {
    addMessage(message, 'user'); // Display user message
    messageInput.value = '';

    // Display "waiting..." message
    const waitingMessageElement = document.createElement('div');
    waitingMessageElement.classList.add('message', 'bot-message');
    waitingMessageElement.textContent = 'Bot: thinking...';
    chatMessages.appendChild(waitingMessageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom

    try {
      const response = await fetch("/api/process_input", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          input: message,
          email: userUID, // Use the UID obtained from the custom event
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const botMessage =
          data.response ||
          data.reminders ||
          data.error ||
          "No response";

        // Replace "thinking..." message with the actual bot response
        // Remove the previous message
        waitingMessageElement.textContent = '';
        
        // Animate the bot's response
        animateResponse(waitingMessageElement, botMessage);

        // Refresh reminders list to include any new reminders
        fetchAndDisplayReminders(userUID);
      } else {
        waitingMessageElement.textContent = "Server returned an error: " + response.status;
      }
    } catch (error) {
      waitingMessageElement.textContent = "An error occurred: " + error.message;
    }
  }
});

// Event listener for reminders list
document.getElementById('remindersList').addEventListener('click', (e) => {
  if (e.target.classList.contains('delete-btn')) {
    const id = e.target.dataset.id;
    deleteReminder(userUID, id);
  }
});

// Function to delete a reminder from Firestore
async function deleteReminder(userUID, reminderId) {
  try {
    const reminderRef = doc(db, "users", userUID, "reminders", reminderId);
    await deleteDoc(reminderRef);
    fetchAndDisplayReminders(userUID); // Refresh reminders list after deletion
  } catch (error) {
    console.error("Error deleting reminder:", error);
  }
}
