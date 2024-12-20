import React from "react";
import styles from "../styles/style";

import {
  Hero,
} from "../components";

export default function Home() {
    return (
      // A div to wrap the entire application
    <div className="w-full overflow-hidden bg-">
      <section>
        <div className={`${styles.flexStart}`}>
          <div className={`${styles.boxWidth}`}>
            <Hero />
          </div>
        </div>

        <div className={`${styles.flexCenter} ${styles.paddingX} `}>
          <div className={`${styles.boxWidth}`}>
          </div>
        </div>

      </section>
    </div>

    );
}
