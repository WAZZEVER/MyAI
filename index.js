const express = require("express");
const path = require("path");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_API_URL =
    "https://f8064f35-6114-412d-a6d8-f8e63573688a-00-jw1z0b4l1ao0.kirk.replit.dev"; // URL for the Python API

// Middleware to parse JSON bodies
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Serve static files from the "public" directory
app.use(express.static(path.join(__dirname, "sec_public")));

// Define routes for different HTML files
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "sec_public", "index.html"));
});

// Define routes for different HTML filesa
app.get("/app", (req, res) => {
    res.sendFile(path.join(__dirname, "sec_public", "app.html"));
});

app.post("/api/process_input", async (req, res) => {
    const userInput = req.body.input;
    const userEmail = req.body.email;

    try {
        const response = await axios.post(`${PYTHON_API_URL}/process_input`, {
            input: userInput,
            email: userEmail,
        });
        res.json(response.data);
    } catch (error) {
        console.error(`Error calling FastAPI /process_input: ${error.message}`);
        console.error(
            error.response
                ? error.response.data
                : "No additional error information",
        );
        res.status(500).json({ error: "Error processing input" });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
