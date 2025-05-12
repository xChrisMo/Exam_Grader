/**
 * Exam Grader Web Application
 * Main JavaScript file
 */

document.addEventListener("DOMContentLoaded", function () {
  // Handle file upload areas - only for drag and drop
  // (click handling is in index.html to avoid duplicate submissions)
  const fileUploadAreas = document.querySelectorAll(".file-upload-area");
  fileUploadAreas.forEach((area) => {
    const input = area.querySelector('input[type="file"]');
    if (input) {
      // Only handle drag and drop events here
      area.addEventListener("dragover", (e) => {
        e.preventDefault();
        area.classList.add("border-primary");
        area.classList.add("bg-light");
      });

      area.addEventListener("dragleave", () => {
        area.classList.remove("border-primary");
        area.classList.remove("bg-light");
      });

      area.addEventListener("drop", (e) => {
        e.preventDefault();
        area.classList.remove("border-primary");
        area.classList.remove("bg-light");

        if (e.dataTransfer.files.length > 0) {
          input.files = e.dataTransfer.files;

          // Trigger the change event instead of submitting directly
          const event = new Event("change", { bubbles: true });
          input.dispatchEvent(event);
        }
      });
    }
  });

  // Handle confirmation dialogs
  const confirmButtons = document.querySelectorAll("[data-confirm]");
  confirmButtons.forEach((button) => {
    button.addEventListener("click", (e) => {
      const message = button.getAttribute("data-confirm");
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // Show loading overlay on form submissions
  const forms = document.querySelectorAll("form:not(.no-loading)");
  forms.forEach((form) => {
    form.addEventListener("submit", () => {
      const loadingOverlay = document.getElementById("loadingOverlay");
      if (loadingOverlay) {
        loadingOverlay.classList.remove("d-none");
        loadingOverlay.classList.add("d-flex");
      }
    });
  });

  // Dismiss alerts automatically after 5 seconds
  const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
  alerts.forEach((alert) => {
    setTimeout(() => {
      const closeButton = alert.querySelector(".btn-close");
      if (closeButton) {
        closeButton.click();
      }
    }, 5000);
  });

  // Save session data to localStorage when navigating away
  window.addEventListener("beforeunload", function () {
    // Get session data from the page
    const sessionData = {};

    // Check for guide content
    const guideContent = document.querySelector(".guide-content");
    if (guideContent) {
      sessionData.guideContent = guideContent.textContent;
    }

    // Check for submission content
    const submissionContent = document.querySelector(".submission-content");
    if (submissionContent) {
      sessionData.submissionContent = submissionContent.textContent;
    }

    // Check for mapping result
    const mappingResult = document.querySelector("#mappingResult");
    if (mappingResult) {
      sessionData.mappingResult = mappingResult.textContent;
    }

    // Check for grading result
    const gradingResult = document.querySelector("#gradingResult");
    if (gradingResult) {
      sessionData.gradingResult = gradingResult.textContent;
    }

    // Save to localStorage if we have data
    if (Object.keys(sessionData).length > 0) {
      localStorage.setItem(
        "examGraderSessionData",
        JSON.stringify(sessionData)
      );
    }
  });

  // Restore session data from localStorage when page loads
  const sessionData = localStorage.getItem("examGraderSessionData");
  if (sessionData) {
    try {
      const data = JSON.parse(sessionData);

      // Restore guide content if needed
      if (data.guideContent) {
        const guideContent = document.querySelector(".guide-content");
        if (guideContent && !guideContent.textContent.trim()) {
          guideContent.textContent = data.guideContent;
        }
      }

      // Restore submission content if needed
      if (data.submissionContent) {
        const submissionContent = document.querySelector(".submission-content");
        if (submissionContent && !submissionContent.textContent.trim()) {
          submissionContent.textContent = data.submissionContent;
        }
      }

      // Restore mapping result if needed
      if (data.mappingResult) {
        const mappingResult = document.querySelector("#mappingResult");
        if (mappingResult && !mappingResult.textContent.trim()) {
          mappingResult.textContent = data.mappingResult;
        }
      }

      // Restore grading result if needed
      if (data.gradingResult) {
        const gradingResult = document.querySelector("#gradingResult");
        if (gradingResult && !gradingResult.textContent.trim()) {
          gradingResult.textContent = data.gradingResult;
        }
      }
    } catch (e) {
      console.error("Error restoring session data:", e);
    }
  }
});
