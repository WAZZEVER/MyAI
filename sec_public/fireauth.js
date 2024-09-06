// Import Firebase modules
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.1/firebase-app.js";
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

// Your Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyATy2cptl-YJkRrE4w-9A21ftnTbyjJoJY",
  authDomain: "myai-35dfc.firebaseapp.com",
  projectId: "myai-35dfc",
  storageBucket: "myai-35dfc.appspot.com",
  messagingSenderId: "578833665589",
  appId: "1:578833665589:web:4f35749090353c0fedab7c",
  measurementId: "G-Q6Q3DY5WL0",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { auth, db};
