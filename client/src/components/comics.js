import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

export default function Comics() {
  const router = useRouter();
  const [images, setImages] = useState([]);

  useEffect(() => {
    // Retrieve images from localStorage
    const storedImages = localStorage.getItem('generatedComics');
    
    if (storedImages) {
      try {
        const parsedImages = JSON.parse(storedImages);
        // Convert to base64 image URLs
        const base64Images = parsedImages.map(base64Image => 
          `data:image/png;base64,${base64Image}`
        );
        setImages(base64Images);
      } catch (error) {
        console.error('Error parsing images', error);
      }
    } else {
      // If no images, redirect back to dashboard
      console.log("no image");
    }

    // Optional: Clear localStorage after retrieving
    return () => {
      localStorage.removeItem('generatedComics');
    };
  }, [router]);

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="container mx-auto">
        <div className="mb-6">
          <button 
            onClick={() => router.push('/')} 
            className="bg-cyan-600 hover:bg-teal-900 text-white py-2 px-4 rounded-full"
          >
            Back to Dashboard
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {images.map((image, index) => (
    <div key={index} className="image-item">
      <img
        src={image}
        alt={`Generated comic ${index + 1}`}
        className="rounded-lg shadow-md w-full h-full object-contain"
      />
    </div>
  ))}
</div>
      </div>
    </main>
  );
}