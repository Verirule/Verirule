import type { AppProps } from "next/app";
import Head from "next/head";

import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>Verirule</title>
        <meta
          name="description"
          content="Automated regulatory compliance monitoring"
        />
        <link rel="icon" href="/branding/favicon.ico" />
      </Head>
      <Component {...pageProps} />
    </>
  );
}
