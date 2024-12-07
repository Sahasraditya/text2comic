import "@/styles/globals.css";
import Footer from "@/components/Footer";
import { Analytics } from '@vercel/analytics/react';

export default function App({ Component, pageProps }) {
  return (
    <>
      {/* <Navbar /> */}
      <Component {...pageProps} />
      {/* <Analytics /> */}
      <Footer />
    </>
  );
}
