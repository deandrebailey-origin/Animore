/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: { root: __dirname },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 's4.anilist.co',
        port: '',
        pathname: '**',
      },
    ],
  },
};

module.exports = nextConfig;

//This is a security feature of Next.js. To use an external 
//image, you must explicitly tell Next.js which domains are allowed. 
//The error message is very clear: the hostname s4.anilist.co