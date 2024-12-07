import styles from "../styles/style";
import { useRouter } from "next/router";
import { useEffect } from "react";


// lottie config
const Hero = () => {
  const router = useRouter()

  useEffect(() => {
    document.title = "Text2Comic";
  }, []);

  return (
    <section
      id="home"
      className={`flex items-center justify-center h-screen ${styles.paddingY}`}
    >
      <div className="flex flex-col items-center">
        <button
          className="bg-cyan-600 hover:bg-teal-900 text-white py-3 px-6 rounded-full drop-shadow-2xl font-poppins font-semibold text-3xl"
          onClick={() => router.push("/dashboard")}
        >
          Get Started
        </button>
      </div>
    </section>
  );
};

export default Hero;
