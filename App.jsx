import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
const CATEGORIES = [
  { id: "all", label: "All Services" },
  { id: "cleaning", label: "🧹 Cleaning" },
  // { id: "shifting", label: "📦 Shifting" },
  // { id: "repairs", label: "🔧 Repairs" },
  // { id: "other", label: "✨ Other" },
];
const TIME_SLOTS = [
  "8:00 AM – 10:00 AM",
  "10:00 AM – 12:00 PM",
  "12:00 PM – 2:00 PM",
  "2:00 PM – 4:00 PM",
  "4:00 PM – 6:00 PM",
  "6:00 PM – 8:00 PM",
];
const SERVICE_AREAS = [
  "Gandhi Bazaar",
  "Gopala",
  "Vinobanagar",
  "Nehru Road",
  "Kuvempunagar",
  "Jayanagar",
  "Durgigudi",
  "KR Puram",
  "BH Road",
  "Sagara Road",
  "Tilak Nagar",
  "Vidya Nagar",
];

const ALLOWED_SERVICES = [
  { id: 1, name: "Full Home Deep Cleaning", icon: "🏠", price: 1499, unit: "starting", category: "cleaning", description: "Complete deep cleaning of bedrooms, hall, kitchen & bathrooms with professional equipment." },
  { id: 2, name: "Bathroom Cleaning", icon: "🚿", price: 199, unit: "starting", category: "cleaning", description: "Tile scrubbing, stain removal, sanitisation of toilets, sinks and fittings." },
  { id: 3, name: "Kitchen Cleaning", icon: "🍳", price: 399, unit: "starting", category: "cleaning", description: "Make your counters, cabinets and cooking space shine again." },
  { id: 4, name: "Sofa & Carpet Cleaning", "icon": "🛋️", price: 299, unit: "starting", category: "cleaning", description: "Lift dust and stains from your favorite soft furnishings." },
];
const ALLOWED_SERVICE_IDS = new Set(ALLOWED_SERVICES.map((s) => s.id));

const initialForm = {
  name: "",
  phone: "",
  email: "",
  service_id: "",
  address: "",
  preferred_date: "",
  time_slot: "",
  instructions: "",
};
const initialReviewForm = { booking_id: "", phone: "", comment: "", consent: false };

function App() {
  const [services, setServices] = useState(ALLOWED_SERVICES);
  const [servicesStatus, setServicesStatus] = useState("loaded");
  const [servicesError, setServicesError] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [bookingStatus, setBookingStatus] = useState("idle");
  const [bookingMessage, setBookingMessage] = useState("");
  const [reviews, setReviews] = useState([]);
  const [reviewsStatus, setReviewsStatus] = useState("loading");
  const [reviewForm, setReviewForm] = useState(initialReviewForm);
  const [reviewStatus, setReviewStatus] = useState("idle");
  const [reviewMessage, setReviewMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadServices() {
      try {
        const response = await fetch(`${API_BASE}/api/services`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error("We couldn’t load services right now. Please try again.");
        }
        const data = await response.json();
        if (Array.isArray(data)) {
          // Strictly allow only the 4 cleaning services on screen
          const filtered = data.filter((item) => ALLOWED_SERVICE_IDS.has(Number(item.id)));
          setServices(filtered.length > 0 ? filtered : ALLOWED_SERVICES);
          setServicesStatus("loaded");
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          // Fall back gracefully to the 4 allowed services
          setServices(ALLOWED_SERVICES);
          setServicesStatus("loaded");
        }
      }
    }

    loadServices();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadReviews() {
      try {
        const response = await fetch(`${API_BASE}/api/reviews`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error("We couldn’t load customer feedback right now.");
        }
        const data = await response.json();
        if (!Array.isArray(data)) {
          throw new Error("Customer feedback returned an unexpected response.");
        }
        setReviews(data);
        setReviewsStatus("loaded");
      } catch (error) {
        if (error.name !== "AbortError") {
          setReviewsStatus("error");
        }
      }
    }

    loadReviews();
    return () => controller.abort();
  }, []);

  const visibleServices = useMemo(
    () =>
      activeCategory === "all"
        ? services
        : services.filter((service) => service.category === activeCategory),
    [activeCategory, services],
  );
  const currentDate = new Date();
  const today = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}-${String(currentDate.getDate()).padStart(2, "0")}`;

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    if (bookingStatus !== "idle") {
      setBookingStatus("idle");
      setBookingMessage("");
    }
  }

  function selectService(serviceId) {
    setForm((current) => ({ ...current, service_id: String(serviceId) }));
    setBookingStatus("idle");
    setBookingMessage("");
  }

  async function submitBooking(event) {
    event.preventDefault();
    setBookingStatus("loading");
    setBookingMessage("");

    try {
      const response = await fetch(`${API_BASE}/api/book`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "We couldn’t confirm your booking. Please try again.");
      }
      const emailSent = data.notifications?.email === true;
      const smsSent = data.notifications?.sms === true;
      const notificationMessage =
        emailSent && smsSent
          ? "Our team was notified by email and SMS."
          : emailSent
            ? "Our team was notified by email."
            : smsSent
              ? "Our team was notified by SMS."
              : "Our team will call to confirm your appointment.";
      setBookingMessage(
        `Booking received! Reference #${data.booking_id}. ${notificationMessage} You can leave feedback after the service is marked complete.`,
      );
      setBookingStatus("success");
      setForm(initialForm);
    } catch (error) {
      setBookingMessage(error.message || "Unable to submit your booking. Please try again.");
      setBookingStatus("error");
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    setReviewStatus("loading");
    setReviewMessage("");

    try {
      const response = await fetch(`${API_BASE}/api/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reviewForm),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "We couldn’t submit your feedback. Please try again.");
      }
      setReviews((current) => [data.review, ...current]);
      setReviewsStatus("loaded");
      setReviewMessage("Thank you. Your feedback has been published.");
      setReviewStatus("success");
      setReviewForm(initialReviewForm);
    } catch (error) {
      setReviewMessage(error.message || "Unable to submit your feedback. Please try again.");
      setReviewStatus("error");
    }
  }

  function closeMobileMenu() {
    setMobileMenuOpen(false);
  }

  return (
    <>
      <header className="site-header">
        <nav className="nav container" aria-label="Main navigation">
          <a className="brand" href="#home" onClick={closeMobileMenu} aria-label="HouseKeep home">
            <img
                  className="brand-house"
                  src="\bc.png"
                  alt="BC logo"
                />
            {/* <span>Bhoomika<span className="brand-highlight">Communication</span></span> */}
            {/* <span className="city-badge">SHIMOGA</span> */}
          </a>
          <button
            className="menu-toggle"
            type="button"
            aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            {mobileMenuOpen ? "✕" : "☰"}
          </button>
          <div className={`nav-links ${mobileMenuOpen ? "nav-links-open" : ""}`}>
            {[
              ["Home", "#home"],
              ["Services", "#services"],
              ["How It Works", "#how-it-works"],
              ["Why Us", "#why-us"],
              ["Book Now", "#booking"],
              ["Contact", "#contact"],
            ].map(([label, href]) => (
              <a href={href} key={label} onClick={closeMobileMenu}>
                {label}
              </a>
            ))}
            <a className="button nav-call" href="tel:+918867572830" onClick={closeMobileMenu}>
              📞 +91 88675 72830
            </a>
          </div>
        </nav>
      </header>

      <main>
        <section className="hero" id="home">
          <div className="container hero-layout">
            <div className="hero-copy">
              <span className="eyebrow hero-eyebrow">✨ Shimoga’s Trusted Home Services</span>
              <h1>
                Your Home, <span>Our Care</span> — Clean, Shift &amp; Repair Made Easy
              </h1>
              <p className="hero-description">
                From a sparkling clean to a stress-free move, Shimoga’s trusted local pros are
                just one booking away.
              </p>
              <div className="hero-actions">
                <a className="button" href="#booking">Book a Service <span>→</span></a>
                <a className="button button-outline" href="#services">Explore Services</a>
              </div>
              <div className="stats-row" aria-label="HouseKeep service statistics">
                <div><strong>5,000+</strong><span>Jobs Done</span></div>
                <div><strong>4.8<span className="stat-star">★</span></strong><span>Avg. Rating</span></div>
                <div><strong>60+</strong><span>Verified Pros</span></div>
                <div><strong>100%</strong><span>Shimoga Local</span></div>
              </div>
            </div>
            <div className="hero-visual" aria-label="Popular home services">
              <div className="hero-glow" />
              <div className="hero-image-wrap">
                <img
                  className="hero-image"
                  src="https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=900&q=80"
                  alt="Professional home cleaning and maintenance service"
                />
              </div>
              <div className="float-card float-card-clean">🧹 <span>Deep Cleaning<small>from ₹1,499</small></span></div>
              <div className="float-card float-card-shift">🍳 <span>Kitchen Cleaning<small>from ₹399</small></span></div>
              <div className="hero-center-card">
                <span className="tool-emoji">✨</span>
                <h2>Clean Homes,<br />One Call Away</h2>
                <p>Same-day service available across Shimoga</p>
                <div className="availability"><span /> Local pros, ready to help</div>
              </div>
              <div className="float-card float-card-repair">🛋️ <span>Sofa & Carpet<small>from ₹299</small></span></div>
              <span className="hero-sparkle sparkle-one">✦</span>
              <span className="hero-sparkle sparkle-two">✧</span>
            </div>
          </div>
        </section>

        <section className="section services-section" id="services">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">WHAT WE DO</span>
              <h2>Our Services</h2>
              <p>Everything your home needs, delivered by people you can trust.</p>
            </div>
            {/* <div className="filter-row" aria-label="Filter services by category">
              {CATEGORIES.map((category) => (
                <button
                  className={`filter-pill ${activeCategory === category.id ? "filter-active" : ""}`}
                  type="button"
                  key={category.id}
                  aria-pressed={activeCategory === category.id}
                  onClick={() => setActiveCategory(category.id)}
                >
                  {category.label}
                </button>
              ))}
            </div> */}
            {servicesStatus === "loading" && <p className="status-message">Loading services…</p>}
            {servicesStatus === "error" && (
              <div className="status-message error-message" role="alert">{servicesError}</div>
            )}
            {servicesStatus === "loaded" && visibleServices.length === 0 && (
              <p className="status-message">No services found in this category.</p>
            )}
            {servicesStatus === "loaded" && visibleServices.length > 0 && (
              <div className="service-grid">
                {visibleServices.map((service) => (
                  <article className="service-card" key={service.id}>
                    <div className="service-icon" aria-hidden="true">{service.icon}</div>
                    <h3>{service.name}</h3>
                    <p>{service.description}</p>
                    <div className="service-card-bottom">
                      <strong>₹{Number(service.price).toLocaleString("en-IN")} <span>{service.unit ? `/${service.unit}` : "starting"}</span></strong>
                      <button
                        className="button button-small"
                        type="button"
                        onClick={() => {
                          selectService(service.id);
                          document.getElementById("booking").scrollIntoView({ behavior: "smooth" });
                        }}
                      >
                        Book Now
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="how-section" id="how-it-works">
          <div className="container">
            <div className="section-heading section-heading-dark">
              <span className="eyebrow eyebrow-gold">SIMPLE &amp; STRESS-FREE</span>
              <h2>How It Works</h2>
              <p>Quality home care in four easy steps.</p>
            </div>
            <div className="steps-grid">
              {[
                ["📱", "Book Online", "Choose a service, date and time that work for you."],
                ["📋", "Get Confirmation", "We’ll call to confirm your booking and details."],
                ["🧑‍🔧", "Pro Arrives", "A verified local professional arrives on time."],
                ["✅", "Relax & Pay", "Enjoy the results and pay after the service."],
              ].map(([emoji, title, text], index) => (
                <article className="step-card" key={title}>
                  <span className="step-number">0{index + 1}</span>
                  <div className="step-icon">{emoji}</div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section why-section" id="why-us">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">THE HOUSEKEEP DIFFERENCE</span>
              <h2>Good People. Great Service.</h2>
              <p>Thoughtful home care from your neighbors in Shimoga.</p>
            </div>
            <div className="why-grid">
              {[
                ["🛡️", "Verified Professionals", "Background-checked experts you can feel good about welcoming in."],
                ["💰", "Transparent Pricing", "Clear starting prices and no surprise charges on your bill."],
                ["⏰", "On-Time Every Time", "We respect your schedule and arrive when we say we will."],
                ["🔄", "Service Guarantee", "Not quite right? Let us know and we’ll make it right."],
                ["🧰", "Own Equipment", "Our pros arrive prepared with the right tools for the job."],
                ["🏠", "Locally Rooted", "A friendly Shimoga team that knows and cares for our community."],
              ].map(([emoji, title, text]) => (
                <article className="why-card" key={title}>
                  <span className="why-icon">{emoji}</span>
                  <div><h3>{title}</h3><p>{text}</p></div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="booking-section" id="booking">
          <div className="container booking-layout">
            <div className="booking-copy">
              <span className="eyebrow booking-eyebrow">LET’S GET STARTED</span>
              <h2>Book a Service</h2>
              <p>Tell us what you need. We’ll take it from there.</p>
              <ul className="booking-benefits">
                <li>✅ No advance payment</li>
                <li>✅ Service 7 days a week</li>
                <li>✅ All Shimoga localities</li>
              </ul>
              <a className="call-box" href="tel:+918867572830">
                <span>Prefer to talk?</span>
                <strong>📞 Call +91 8867572830</strong>
              </a>
            </div>
            <form className="booking-form" onSubmit={submitBooking}>
              <h3>Your booking details</h3>
              <p className="form-intro">We’ll call to confirm your appointment.</p>
              <div className="form-grid">
                 <label>
  Name
  <input
    name="name"
    value={form.name}
    onChange={updateForm}
    required
    autoComplete="name"
    placeholder="Your full name"
  />
</label>
                <label>
  Phone
  <input
    name="phone"
    value={form.phone}
    onChange={updateForm}
    required
    type="tel"
    inputMode="numeric"
    autoComplete="tel-national"
    pattern="[0-9]{10}"
    maxLength={10}
    title="Enter a 10-digit Indian mobile number."
    placeholder="10-digit mobile number"
  />
</label>
                <label>
  Email
  <input
    name="email"
    value={form.email}
    onChange={updateForm}
    required
    type="email"
    autoComplete="email"
    placeholder="you@example.com"
  />
</label>
               <label>
  Service
  <select
    name="service_id"
    value={form.service_id}
    onChange={updateForm}
    required
  >
    <option value="">Select a service</option>
    {services.map((service) => (
      <option key={service.id} value={service.id}>
        {service.icon} {service.name}
      </option>
    ))}
  </select>
</label>
                <label className="full-field">
                  Address in Shimoga <span>*</span>
                  <textarea name="address" value={form.address} onChange={updateForm} required rows="3" autoComplete="street-address" placeholder="House / street, area, Shimoga" />
                </label>
                <label>
                  Preferred Date <span>*</span>
                  <input name="preferred_date" value={form.preferred_date} onChange={updateForm} required type="date" min={today} />
                </label>
                <label>
                  Time Slot <span>*</span>
                  <select name="time_slot" value={form.time_slot} onChange={updateForm} required>
                    <option value="">Choose a time</option>
                    {TIME_SLOTS.map((slot) => <option key={slot} value={slot}>{slot}</option>)}
                  </select>
                </label>
                <label className="full-field">
                  Special Instructions <small>(optional)</small>
                  <textarea name="instructions" value={form.instructions} onChange={updateForm} rows="2" placeholder="Anything we should know before we arrive?" />
                </label>
              </div>
              {bookingMessage && (
                <div className={`form-feedback ${bookingStatus === "success" ? "feedback-success" : "feedback-error"}`} role={bookingStatus === "success" ? "status" : "alert"}>
                  {bookingMessage}
                </div>
              )}
              <button className="button submit-button" type="submit" disabled={bookingStatus === "loading"}>
                {bookingStatus === "loading" ? "Booking…" : "Confirm My Booking →"}
              </button>
              <p className="form-note">🔒 Your details are safe with us.</p>
            </form>
          </div>
        </section>

        <section className="section reviews-section" id="reviews">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">CUSTOMER FEEDBACK</span>
              <h2>Share Your Experience</h2>
              <p>Feedback is available after your booked service is marked complete.</p>
            </div>
            <form className="review-form" onSubmit={submitReview}>
              <h3>Your completed booking</h3>
              <p className="form-intro">Enter the booking reference and phone number used to book.</p>
              <div className="form-grid">
                <label>
                  Booking reference <span>*</span>
                  <input
                    name="booking_id"
                    type="number"
                    min="1"
                    value={reviewForm.booking_id}
                    onChange={(event) => setReviewForm((current) => ({ ...current, booking_id: event.target.value }))}
                    required
                    placeholder="For example, 12"
                  />
                </label>
                <label>
                  Booking phone number <span>*</span>
                  <input
                    name="phone"
                    type="tel"
                    inputMode="numeric"
                    pattern="[0-9]{10}"
                    maxLength={10}
                    value={reviewForm.phone}
                    onChange={(event) => setReviewForm((current) => ({ ...current, phone: event.target.value }))}
                    required
                    placeholder="10-digit mobile number"
                  />
                </label>
                <label className="full-field">
                  Your feedback <span>*</span>
                  <textarea
                    name="comment"
                    value={reviewForm.comment}
                    onChange={(event) => setReviewForm((current) => ({ ...current, comment: event.target.value }))}
                    required
                    maxLength={1000}
                    rows="4"
                    placeholder="Tell us about your completed service"
                  />
                </label>
                <label className="review-consent full-field">
                  <input
                    name="consent"
                    type="checkbox"
                    checked={reviewForm.consent}
                    onChange={(event) => setReviewForm((current) => ({ ...current, consent: event.target.checked }))}
                    required
                  />
                  I agree to display my first name and feedback publicly.
                </label>
              </div>
              {reviewMessage && (
                <div className={`form-feedback ${reviewStatus === "success" ? "feedback-success" : "feedback-error"}`} role={reviewStatus === "success" ? "status" : "alert"}>
                  {reviewMessage}
                </div>
              )}
              <button className="button submit-button" type="submit" disabled={reviewStatus === "loading"}>
                {reviewStatus === "loading" ? "Submitting…" : "Submit feedback"}
              </button>
            </form>
            <div className="review-list" aria-live="polite">
              {reviewsStatus === "loading" && <p className="status-message">Loading customer feedback…</p>}
              {reviewsStatus === "error" && <p className="status-message">Customer feedback is temporarily unavailable.</p>}
              {reviewsStatus === "loaded" && reviews.length === 0 && (
                <p className="status-message">No customer feedback has been shared yet.</p>
              )}
              {reviewsStatus === "loaded" && reviews.map((review) => (
                <article className="review-item" key={review.id}>
                  <blockquote>“{review.comment}”</blockquote>
                  <div className="review-byline">
                    <strong>{review.name}</strong>
                    <span>{review.service_name} · {new Date(review.created_at).toLocaleDateString("en-IN")}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="areas-section" id="areas">
          <div className="container">
            <div className="section-heading">
              <span className="eyebrow">RIGHT AROUND THE CORNER</span>
              <h2>📍 Areas We Serve in Shimoga</h2>
              <p>Local service, wherever you call home.</p>
            </div>
            <div className="area-chips">
              {SERVICE_AREAS.map((area) => <span className="area-chip" key={area}>{area}</span>)}
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer" id="contact">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-brand">
              <a className="brand footer-logo" href="#home">
                <span className="brand-house">🏡</span>
                <span>House<span className="brand-highlight">Keep</span></span>
              </a>
              <p>Your home, our care. Making everyday home services easy for every family in Shimoga.</p>
              <span className="footer-local">Made with care in Shimoga 💚</span>
            </div>
            <div className="footer-column">
              <h3>Quick Links</h3>
              <a href="#home">Home</a>
              <a href="#services">Our Services</a>
              <a href="#how-it-works">How It Works</a>
              <a href="#why-us">Why HouseKeep</a>
              <a href="#booking">Book a Service</a>
            </div>
            <div className="footer-column">
              <h3>Contact Us</h3>
              <a href="tel:+918867572830">📞 +91 88675 72830</a>
              <a href="mailto:anoopbr2002@gmail.com">✉️ anoopbr2002@gmail.com</a>
              <span>📍 Shimoga, Karnataka 577201</span>
            </div>
            <div className="footer-column">
              <h3>Service Hours</h3>
              <span>🕖 Mon–Sun: 7 AM–9 PM</span>
              <span>🚨 Emergency: 24×7</span>
              <span className="footer-note">Here when home needs us.</span>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© 2025 HouseKeep Shimoga. All rights reserved.</span>
            <a href="#home">Back to top ↑</a>
          </div>
        </div>
      </footer>
    </>
  );
}

export default App;
