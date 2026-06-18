async function loadSiteData() {
  const response = await fetch("site-data.json");
  if (!response.ok) {
    throw new Error("Could not load site-data.json");
  }
  return response.json();
}

function phoneHref(phone) {
  const digits = (phone || "").replace(/[^\d+]/g, "");
  return digits ? `tel:${digits}` : "#";
}

function render(data) {
  document.title = `${data.businessName} | ${data.meta?.niche || "Local Service"}`;
  document.getElementById("brand").textContent = data.businessName;
  document.getElementById("tagline").textContent = data.tagline || "Trusted local professionals";
  document.getElementById("hero-headline").textContent = data.hero?.headline || data.businessName;
  document.getElementById("hero-subtext").textContent = data.hero?.subtext || "";

  const ctaText = data.ctaText || "Call Now";
  const ctaHref = phoneHref(data.contact?.phone);
  document.getElementById("header-cta").textContent = ctaText;
  document.getElementById("header-cta").href = ctaHref;
  document.getElementById("hero-cta").textContent = ctaText;
  document.getElementById("hero-cta").href = ctaHref;

  const rating = data.social_proof?.rating;
  const reviews = data.social_proof?.reviews;
  if (rating) {
    const ratingBlock = document.getElementById("rating-block");
    ratingBlock.hidden = false;
    document.getElementById("rating-text").textContent = reviews
      ? `${rating} stars from ${reviews} reviews`
      : `${rating} star rating`;
  }

  const servicesGrid = document.getElementById("services-grid");
  servicesGrid.innerHTML = (data.services || [])
    .map(
      (service) => `
        <article class="service-card">
          <h3>${service.title}</h3>
          <p>${service.description}</p>
        </article>
      `,
    )
    .join("");

  document.getElementById("about-title").textContent = data.about?.title || "About Us";
  document.getElementById("about-text").textContent = data.about?.text || "";
  document.getElementById("contact-phone").textContent = data.contact?.phone || "";
  document.getElementById("contact-address").textContent = data.contact?.address || "";
  document.getElementById("contact-city").textContent = data.contact?.city || "";
  document.getElementById("footer-text").textContent =
    `© ${new Date().getFullYear()} ${data.businessName}. All rights reserved.`;
}

loadSiteData().then(render).catch((error) => {
  document.body.innerHTML = `<main class="container" style="padding:4rem 0"><h1>Site not generated yet</h1><p>${error.message}</p></main>`;
});
