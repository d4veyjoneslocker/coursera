export default function PrivacyPolicyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-12 text-[#343332]">
      <h1 className="text-4xl font-semibold mb-4">Privacy Policy</h1>

      <p className="text-sm text-[#705C4F] mb-8">
        Last updated: May 27, 2026
      </p>

      <div className="space-y-6 text-base leading-7">
        <div>
          <p>
            We built this product to help teams make better decisions with their
            data.
          </p>

          <p className="mt-4">
            Respecting your data is a core part of that. We only collect what we
            need to improve the product and make it work reliably — nothing
            more.
          </p>
        </div>

        <hr className="border-[#E5DDD0]" />

        <section>
          <h2 className="text-2xl font-semibold mb-3">Overview</h2>

          <p>
            We take your privacy seriously. This Privacy Policy explains what
            information we collect, how we use it, and how we protect it when
            you use our platform.
          </p>

          <p className="mt-4">
            Our goal is simple: use data to improve your experience — not to
            misuse or sell your information.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">
            Information We Collect
          </h2>

          <h3 className="text-xl font-medium mt-6 mb-2">1. Usage Data</h3>

          <p>
            When you use the platform, we automatically collect information
            about how the app is used.
          </p>

          <ul className="list-disc pl-6 mt-3 space-y-1">
            <li>Pages you visit</li>
            <li>Features you interact with</li>
            <li>General interaction patterns</li>
            <li>Session duration and activity timing</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-2">
            2. Session Recordings
          </h3>

          <p>
            We may use session replay tools to better understand how users
            interact with the app.
          </p>

          <p className="mt-4">
            These recordings do not capture sensitive information such as
            passwords, payment details, or private input fields where
            applicable.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-2">
            3. Device & Technical Information
          </h3>

          <p>
            We may collect basic technical data such as browser type, device
            type, approximate location, and performance metrics.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">
            How We Use This Information
          </h2>

          <ul className="list-disc pl-6 space-y-1">
            <li>Improve product usability and design</li>
            <li>Diagnose bugs and performance issues</li>
            <li>Understand feature usage and prioritize improvements</li>
            <li>Enhance overall user experience</li>
          </ul>

          <p className="mt-4">
            We do not sell your data to third parties.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">Data Sharing</h2>

          <p>
            We use trusted third-party tools to help operate and improve the
            platform. These providers process data on our behalf and are
            required to handle it securely.
          </p>
        </section>

        <section>
            <h2 className="text-2xl font-semibold mb-3">
                Your Business Data
            </h2>

            <p>
                Any business, sales, distributor, retailer, or operational data
                uploaded to the platform remains private to your organization.
            </p>

            <p className="mt-4">
                We do not sell, share, or disclose your proprietary business data
                to other customers, third parties, or external organizations.
            </p>

            <p className="mt-4">
                Third-party services we use to operate the platform (such as
                infrastructure, analytics, or hosting providers) may process
                limited data on our behalf solely for the purpose of providing 
                the service. These providers are not permitted to use
                your business data for their own purposes.
            </p>

            <p className="mt-4">
                Usage analytics and session replay tools are used only to
                understand how the platform itself is being used (for example,
                navigation patterns or feature interactions) and are not intended
                to share or expose your underlying business information externally.
            </p>
            </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">Data Retention</h2>

          <p>
            We retain data only as long as necessary to operate the service,
            improve the product, and comply with legal obligations.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">Your Choices</h2>

          <p>
            You can choose not to use the platform if you are not comfortable
            with this data collection.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">Security</h2>

          <p>
            We take reasonable measures to protect your information from
            unauthorized access, misuse, or disclosure.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">
            Changes to This Policy
          </h2>

          <p>
            We may update this Privacy Policy from time to time. If we do, we’ll
            update the date at the top of this page.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">Contact</h2>

          <p>
            If you have any questions about this policy, feel free to reach out:
          </p>

          <p className="mt-4 font-medium">hello@aisle6analytics.com</p>
        </section>
      </div>
    </main>
  )
}