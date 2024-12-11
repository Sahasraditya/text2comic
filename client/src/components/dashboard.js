import Link from "next/link";
import { useState } from "react";
import { useRouter } from 'next/router';
import Lottie from "react-lottie-player";
import loader from '@/../../public/assets/loader.json';
import CustomizedSnackbars from "./Snackbar";

export default function Dashboard() {
  const [userInput, setUserInput] = useState("");
  const [stableDiffusionKey, setStableDiffusionKey] = useState("");
  const [comicStyle, setComicStyle] = useState("Marvel");
  const [loading, setLoading] = useState(false);
  const [errMessage, setErrMessage] = useState("");
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const submitHandler = async () => {
    try {
      setLoading(true);
      const requestOptions = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userInput: userInput,
          cfgValue: 8,
          steps: 30,
          customizations: comicStyle,
          key: stableDiffusionKey
        }),
        redirect: "follow",
      };
      // const backendUrl = "http://backend-service:5000";  // Use the service name
      // const response = await fetch(`${backendUrl}/`, requestOptions);
      // const response = await fetch("http://127.0.0.1:5000/", requestOptions);
      const response = await fetch("http://backend-service.default.svc.cluster.local", requestOptions);
      if (response.ok) {
        const data = await response.json();
        
        if (data.images && data.images.length > 0) {
          // Store images in localStorage
          localStorage.setItem('generatedComics', JSON.stringify(data.images));
          
          // Navigate to comics page
          router.push('/comics');
        }
  
        setLoading(false);
      } else {
        const errorData = await response.json();
        setErrMessage(errorData.error || "An error occurred");
        setOpen(true);
        setLoading(false);
      }
    } catch (err) {
      setErrMessage(err.message || "Network error");
      setOpen(true);
      setLoading(false);
    }
  };

  const clickHandler = () => {
    if (userInput.length === 0 || stableDiffusionKey.length === 0) {
      setErrMessage("Prompt or Stable Diffusion Key cannot be empty!");
      setOpen(true);
    } else {
      submitHandler();
    }
  };

  return (
    <main className="className=flex items-center justify-center min-h-[80vh]">
      {loading ? (
        <div className="static backdrop-blur-sm min-h-screen flex items-center justify-center flex-col">
          <div className="bg-white opacity-75 h-[38h] w-[38vh] rounded-lg">
            <Lottie loop animationData={loader} play className="h-[40vh]" />
          </div>
          <div className="font-xl text-white font-semibold p-2">
            Your story is coming to life...
          </div>
          <div className="font-xl text-white font-semibold p-2">
            It might take up to a minute, so please be patient
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center">
          <section className="flex flex-col items-center bg-white border border-gray-200 rounded-lg shadow md:flex-row md:max-w-xl hover:bg-gray-100 h-[550px] w-[600px]">
            <div className="flex flex-col h-full w-full p-4 leading-normal">
              <label
                htmlFor="UserMessage"
                className="block text-xs font-medium text-gray-700"
              >
                Prompt*
              </label>
              <textarea
                rows="4"
                cols="50"
                type="text"
                id="UserMessage"
                placeholder="Write a clear and descriptive message about what you would like to see as a comic."
                value={userInput}
                className="mt-1 w-full p-4 rounded-md border-gray-300 shadow-sm sm:text-sm focus:border-indigo-200 h-full"
                onChange={(e) => setUserInput(e.target.value)}
              />
              <label
                htmlFor="comicStyle"
                className="block text-xs font-medium text-gray-700 mt-2"
              >
                Style of the Comic
              </label>
              <select
                id="comicStyle"
                value={comicStyle}
                onChange={(e) => setComicStyle(e.target.value)}
                className="mt-1 w-full p-3 rounded-md border-gray-300 shadow-sm sm:text-sm focus:border-indigo-200"
              >
                <option value="Marvel">Marvel</option>
                <option value="DC">DC</option>
                <option value="Anime">Anime</option>
                <option value="Spider-verse">Spider-verse</option>
                <option value="Archies">Archies</option>
              </select>
              <label
                htmlFor="stableDiffusionKey"
                className="block text-xs font-medium text-gray-700 mt-2"
              >
                Stable Diffusion Key*
              </label>
              <input
                id="stableDiffusionKey"
                type="password"
                placeholder="Enter your stable diffusion key"
                value={stableDiffusionKey}
                onChange={(e) => setStableDiffusionKey(e.target.value)}
                className="mt-1 w-full p-3 rounded-md border-gray-300 shadow-sm sm:text-sm focus:border-indigo-200"
              />
              <button
                className="bg-cyan-600 hover:bg-teal-900 text-white py-2 px-4 rounded-full drop-shadow-2xl font-poppins text-bold mt-6"
                onClick={clickHandler}
              >
                Submit
              </button>
            </div>
          </section>
        </div>
      )}
      <CustomizedSnackbars open={open} setOpen={setOpen} message={errMessage} />
    </main>
  );
}