## **Mixed Miles** 

## **Software Requirements Specification** 

|Document|MixedMiles SRS|
|---|---|
|Platform|iOS & Android & Web|
|Language|English|
|Year|2026|



## **Introduction** 

## 1. **Project Name** 

MixedMiles 

## 2. **Goal of the System** 

MixedMiles is a community-driven mobile platform that connects people through local events, social gatherings, and partner discount experiences. It gives event organizers (City Founders) a structured way to build and monetize local communities, while giving subscribers (Members) exclusive access to events, discounts, property rentals, and community tools. 

## **The system achieves this goal by:** 

- Enabling City Founders to create and manage city-level events through a dedicated web dashboard. 

- Giving Members access to partner discounts (verified by their membership QR code), gatherings, and property listings. 

- Providing Admin with a full oversight dashboard to manage all City Founders, users, and analytics across all countries and cities. 

- Building a social layer — posts, likes, comments, chat — to keep the community engaged between events. 

## **System Overview** 

## **What the App Does — Simple Explanation** 

- A user downloads MixedMiles. They can browse events, posts, and partner listings as a Non-Member. 

- The user subscribes to become a Member, unlocking full access: discount redemption via their personal QR code, gathering creation, and property upload. 

- A City Founder applies from the More menu. Once approved by Admin, they get access to a web dashboard where they create events, manage their team, upload media, and track their community. 

- When a Member attends an event, the ticket is auto-generated with a QR code and delivered via WhatsApp, email and the applecation. 

- Partners scan or check the Member's QR code to verify membership and grant the applicable discount. 

- Admin oversees everything through a web dashboard with charts, filters, and full edit/delete control over all data. 

## **System Components** 

**==> picture [543 x 378] intentionally omitted <==**

**----- Start of picture text -----**<br>
Component Type Who Uses It<br>Mobile App iOS &  All users (Members, Non-Members, City Founders<br>Android browsing)<br>City Founder  Web City Founders — manage events, team, media,<br>Dashboard partners<br>Admin Dashboard Web Platform administrators — full oversight and<br>management<br>Backend API REST /  All clients (mobile + web dashboards)<br>Cloud<br>Push Notifications FCM / APNs All mobile users<br>Payment Gateway Members purchasing tickets or subscriptions<br>WhatsApp / Email Third-party Ticket and invitation delivery<br>**----- End of picture text -----**<br>


## **Users (Actors)** 

**Actor Overview** 


**----- Start of picture text -----**<br>
Actor Platform Who They Are Access Level<br>**----- End of picture text -----**<br>


|**Actor**|**Platform**|**Who They Are**|**Access Level**|
|---|---|---|---|
|||||
|Admin|Web Dashboard|Platform owner/operator with full<br>control over all data, users, and<br>settings.|Full|
|City<br>Founder|Web Dashboard<br>+ Mobile|Verifed event organizer managing a<br>city community and its events.|High|
|Member|Mobile App|Subscribed user — full platform<br>access.|Medium|
|Non-<br>Member|Mobile App|Registered user without active<br>subscription — limited access.|Low|



## **Admin** 

Has full read/write access to all data across all countries and cities. 

- Approves or rejects City Founder applications. 

- Can add, edit, and delete: City Founders, Members, events, partners, and any platform content. 

Views analytics charts and filtered data on a web dashboard. 

## **City Founder** 

- Applies from the mobile app More menu; approved by Admin. 

- Manages their city's community via a dedicated web dashboard. Creates, edits, and deletes events. 

- Manages their team (public speakers and content creators). 

- Adds and manages partner businesses (Guidebook entries). 

- Uploads photos and videos to the Media Area. 

- Reviews and accepts/rejects join requests for their events. 

- Can also post, like, comment, and chat on the mobile app. 

## **Member** 

Pays a subscription to access full platform features. 

- Must submit a join request (No need for a City Founder aprovel) to attend events. Has a personal Membership QR Code used by partners to verify membership and grant discounts. 

- Can create Gatherings if they attend 1 events (max 20 people). Can list and rent Property Rentals. 

- Can post, like, comment, and chat. 

- Can sell and buy products 

## **Non-Member** 

- Can browse the homepage, events, posts, and partner listings. Can like and comment on posts and events. 

- Must submit a join request (City Founder approval) to attend events. Cannot redeem partner discounts. 

- Can create Gatherings if they attend 3 events (max 20 people). Can chat with other users. 

- Can rent proparties. 

- Can brows every thing in the app. 

- Can post, like, comment, and chat. Can sell 1 product and buy products 

## **Functional Requirements** 

Requirements are grouped by feature area and tagged with unique IDs (FR-XXX). 

## **Onboarding & Authentication (MVP Phase 1)** 

**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>1 The app shall display a branded splash screen with the  All<br>MixedMiles logo and slogan.<br>2 All<br>On first launch, the app shall show country selection (default:<br>Your Location).<br>3 Users shall be able to register using email and password. All<br>4 Social sign-in via Google and Apple shall be supported. All<br>5 Users shall be able to log in with registered credentials. All<br>6 Password reset via email shall be supported. All<br>7 After registration, the app shall prompt the user to subscribe  All<br>(Member) or continue as a Non-Member.<br>8 All<br>During the membership subscription flow, the system shall<br>require the user to upload a photo of their national ID or Passport<br>for identity and nationality verification.<br>9 If the uploaded document confirms the applicant is an expatriate  System<br>+ member, the system shall automatically approve the event join<br>without requiring admin review.<br>10 If the uploaded document indicates the applicant is not an  System<br>expatriate, the membership application shall be placed in a<br>pending state and routed to Admin for manual review and<br>approval or rejection.<br>11 The applicant shall receive a notification informing them whether  System<br>their membership was instantly approved or is pending admin<br>review, along with an estimated review timeframe.<br>12 An optional onboarding slideshow (3–5 slides) shall appear after  All<br>first registration.<br>13 Authenticated returning users shall land directly on the Home /  All<br>Feed screen.<br>**----- End of picture text -----**<br>


## **Navigation (MVP Phase 1)** 

|**ID**|**Requirement**|**Actor**|
|---|---|---|
|**14**|**The mobile app shall have a bottom navigation bar with fve tabs:**<br>**Home, Events, Chat, Guidebook, Profle.**|**All**|
|**15**|**The active tab shall be highlighted using the brand color.**|**All**|
|**16**|**All main sections shall be reachable from the bottom bar at any**<br>**time.**|**All**|



## **Home Page (Feed) (MVP Phase 1)** 

The Home page is the primary landing screen. It is public-facing — all users can view its content. 

**==> picture [541 x 600] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>17 The Home page shall display: social posts (images + captions),  All<br>upcoming events in my city, gatherings, store product previews,<br>and property listings in a unified scrollable feed.<br>18 All users shall be able to view posts, events, and gatherings on  All<br>the Home page.<br>19 Comments support a single level of nesting, allowing users to  All<br>reply directly to a parent comment.<br>20 Any registered user shall be able to like and comment on any  All<br>post, event, or gathering.<br>21 Event cards on the Home page shall display: event name,  All<br>description, date, time, area, price, and cover image.<br>22 The Home page shall include a 'Create Gathering' button visible  Member<br>to all users; tapping it shall prompt users who have not yet<br>attended 1 events to do so before they can create a Gathering.<br>23 The Home page shall include a 'Create Gathering' button visible  Non-<br>to all users; tapping it shall prompt users who have not yet  Member<br>attended 3 events to do so before they can create a Gathering.<br>24 The Home page shall display upcoming events in a dedicated  All<br>section or carousel.<br>25 All users shall be able to view their activity history (likes,  All<br>comments, events attended, gatherings) from their Profile.<br>**----- End of picture text -----**<br>


## **Posts & Social Interactions (MVP Phase 1)** 

|**ID**|**Requirement**|**Actor**|
|---|---|---|
|**26**|**Any registered user shall be able to create a post with up to 5**<br>**images and a text caption.**|**All**|
|**27**|**Any registered user shall be able to like a post.**|**All**|
|**28**|**Any registered user shall be able to comment on a post.**|**All**|
|**29**|**Post authors shall receive a push notifcation when their post is**<br>**liked or commented on.**|**All**|
|**30**|**All users shall be able to view a full history of their likes,**<br>**comments, events, and gatherings in their profle.**|**All**|



## **Gatherings (MVP Phase 1)** 

**==> picture [541 x 471] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>31 Any registered Member who has attended at least 1 events shall  Member<br>be able to create a Gathering.<br>32 Any registered Non-Member who has attended at least 3 events  Non-<br>shall be able to create a Gathering. Member<br>33 A Gathering shall include: title, description, date/time, area,  All<br>optional cover image, and max attendees (hard cap: 20).<br>34 The Gathering's exact location (map pin) shall only be visible to  System<br>users who have already joined.<br>35 The system shall reject join requests once a Gathering reaches 20  System<br>attendees.<br>36 Any user shall be able to view, like, and comment on a Gathering  All<br>card from the Home page.<br>37 Any member can join a gathering if they attended 1 event before. Member<br>38 Non-Members can join a gathering if they have attended at least  Non-<br>three events. Member<br>**----- End of picture text -----**<br>


## **Events (Mobile — Attendee Side) (MVP Phase 1)** 

**==> picture [541 x 639] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>37 All users shall be able to browse the Events list and view  All<br>individual event detail pages.<br>38 All<br>Events shall be filterable by city, date range, and category.<br>39 Event detail pages shall display: event name, description, date,  All<br>time, area, price, cover image, and available capacity.<br>40 All users shall be able to view upcoming events. All<br>41 Active Members shall be able to join/purchase tickets to Events  Member<br>instantly without prior approval.<br>42 Non-Members shall submit a join request that the City Founder  Non-<br>must approve before payment is requested. Members<br>43 Upon City Founder approval of a Non-Member join request, the  System<br>applicant shall receive the invitation via WhatsApp and email, and<br>shall also be able to access it inside the app.<br>44 The invitation/ticket shall contain: a QR code to confirm event  System<br>entry and the event's location.<br>45 After successful payment, the system shall auto-generate a  System<br>unique QR-code ticket.<br>46 The ticket shall be delivered to the user via WhatsApp, email and  System<br>application within 60 seconds of payment confirmation.<br>47 Each ticket QR code shall encode the user ID, event ID, and a  System<br>unique tamper-proof token.<br>**----- End of picture text -----**<br>


## **Guidebook & Discount Redemption (MVP Phase 1)** 

Discounts are verified using each Member's personal Membership QR Code — not by scanning a partner QR code. The partner (or their staff) checks the user's QR code to confirm they are an active Member before granting a discount. 

**==> picture [541 x 638] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>48 All<br>The Guidebook shall display a searchable, filterable list of partner<br>businesses.<br>49 Each partner entry shall show: name, logo, discount percentage,  All<br>description, category, city, address, map link, hours and social<br>media link or website.<br>50 All<br>The Guidebook shall support filtering by category and city.<br>51 Each active Member shall have a personal Membership QR Code  Member<br>visible in their Profile.<br>52 The Member's QR Code shall encode their user ID and a server- System<br>validated membership token.<br>53 Partner<br>A partner (or their staff) shall be able to scan or check the<br>Member's QR Code using a provided partner-side tool to verify<br>active membership.<br>54 If the QR code is valid and the user has an active membership, the  System<br>system shall confirm 'Active Member — Discount Applicable'.<br>55 If the QR code belongs to a Non-Member or an expired  System<br>membership, the system shall return 'Not a Member — Discount<br>Not Applicable'.<br>56 Discount redemptions shall be logged with timestamp, user ID,  System<br>and partner ID.<br>57 Non-Members viewing the Guidebook shall see partner listings  Non-<br>Member<br>but shall not be able to use the discount QR verification flow.<br>**----- End of picture text -----**<br>


## **Property Rental (MVP Phase 2)** 

**==> picture [542 x 609] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>58 Any active Member shall be able to list a property or room for  Member<br>rent, providing: title, description, photos, property type (full<br>property or private/shared room), size, number of rooms, price,<br>location, and contact details.<br>59 Members listing a property or room shall be able to specify  Member<br>comprehensive features and amenities, categorized into:<br>Basic Comforts: Air conditioning, heating, ceiling fans,<br>balcony/terrace.<br>Connectivity & Media: High-speed Wi-Fi/Internet, cable TV.<br>Parking & Facilities: Dedicated parking spot, visitor parking,<br>garage, elevator access.<br>Furnishing Status: Fully furnished, semi-furnished, or<br>unfurnished.<br>Security Features: 24/7 security, CCTV surveillance, gated<br>access.<br>Shared/Common Areas (for rooms): Shared kitchen, laundry<br>facilities (washer/dryer), living room access, private or shared<br>bathroom.<br>59 Any user shall be able to browse available property listings. All<br>60 All<br>Property listings shall be searchable and filterable by city, price<br>size, number of rooms, range, and property type.<br>61 Members shall be able to edit or delete their own property  Member<br>listings.<br>62 Users interested in a property shall be able to contact the listing  All<br>owner via in-app chat or a provided contact method.<br>**----- End of picture text -----**<br>


## **Store (MVP Phase 2)** 

The Store allows all registered users to list products for sale. Non-Members may list one product; Members may list an unlimited number. Store items are visible both on the dedicated Store page and in the Home Feed. 

**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>63 Any registered user shall be able to access the Store page from the  All<br>bottom navigation bar or from the Home Feed.<br>64 Any registered Member shall be able to add a product to the Store,  Member<br>providing: product name, description, price, category, photos (up<br>to 5), and contact method.<br>65 Active Members shall be able to list an unlimited number of  Member<br>products in the Store.<br>66 Non-Members shall be limited to listing a maximum of one (1)  Non-<br>active product in the Store at any time. Attempting to add a  Member<br>second product shall display a prompt to subscribe as a Member.<br>67 All users (including non-registered visitors) shall be able to browse  All<br>and view Store product listings.<br>68 All<br>Store listings shall be searchable and filterable by category, price<br>range, and city.<br>69 Store product cards shall appear in the Home Feed alongside  All<br>posts, events, gatherings, and property listings, so all users can<br>discover them without navigating to the dedicated Store page.<br>70 Users interested in a Store product shall be able to contact the  All<br>seller via in-app chat or the contact method provided in the<br>listing.<br>71 Any registered Member shall be able to edit or delete their own  Member<br>Store product listings.<br>72 The system shall notify the seller via push notification when  System<br>another user shows interest in (or contacts them about) their<br>listed product.<br>73 Admin shall be able to view, moderate, and remove any Store  Admin<br>product listing that violates community guidelines.<br>74 Any registered user (Member or Non-Member) shall be able to tap  All<br>**----- End of picture text -----**<br>


**==> picture [541 x 672] intentionally omitted <==**

**----- Start of picture text -----**<br>
"Make an Offer" on any active Store product listing and enter a<br>proposed price.<br>75 The system shall validate that the offer amount is a positive  System<br>number greater than zero before<br>76 Upon submission of an offer, the seller shall receive an in-app  System<br>push notification containing the buyer's username and proposed<br>price.<br>77 The seller shall be able to Accept, Decline, or Counter any  Seller<br>received offer from within the app.<br>78 If the seller chooses to Counter, they shall enter a new price. The  System<br>buyer shall be notified and presented with Accept or Decline<br>options.<br>79 Each product listing may have at most one active accepted offer  System<br>at a time. Accepting an offer shall automatically mark the listing<br>status as "Pending".<br>80 When an offer is accepted, both buyer and seller shall receive  System<br>each other's contact details and a direct-chat shortcut.<br>81 Declined offers shall be silently logged. The buyer shall receive a  System<br>notification that their offer was declined, with no reason required<br>from the seller<br>82 A seller shall be able to cancel an accepted deal; doing so returns  Seller<br>the listing status to "Available" and notifies the buyer<br>83 All<br>The offer history (sent/received offers and their statuses) shall be<br>visible to each user under their Store activity in their Profile.<br>84 Admin<br>Admin shall be able to view offer activity per listing for<br>moderation purposes.<br>**----- End of picture text -----**<br>


## **Chat (MVP Phase 1)** 

**==> picture [541 x 435] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>85 Users must be connected (have added each other) to exchange  All<br>direct messages.<br>86 Messages from connected users shall be delivered directly to the  All<br>Direct Messages inbox.<br>87 All<br>Messages from unconnected users shall be filtered into the<br>Message Requests folder.<br>88 Chat shall support text messages and image attachments. All<br>89 Unread message count shall appear as a badge on the chat icon. All<br>90 All<br>Users shall receive a push notification for new incoming messages.<br>91 Users shall be able to block another user from messaging them. All<br>92 The system shall allow users to follow and unfollow anyone,  All<br>enabling the follower to view the followed user's gatherings and<br>posts.<br>**----- End of picture text -----**<br>


## **Profile (MVP Phase 1)** 

**==> picture [542 x 639] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>93 All<br>Each user shall have a profile showing: photo, name, bio, followers,<br>connect button, count, following count, messages.<br>94 Users shall be able to follow and unfollow other users. All<br>95 Users can follow any other user to see their gatherings and posts in  All<br>their feed.<br>96 Users can contact any other user to request permission to chat with  All<br>them.<br>97 Active Members shall see their personal Membership QR Code on  Member<br>their profile page.<br>98 All<br>The profile shall show membership status (Active / Inactive).<br>99 All<br>The profile shall have tabs for: Posts, Gatherings, Events Attended,<br>and Activity History.<br>100 Activity history shall include: liked posts, comments made, events  All<br>joined, and gatherings created/joined.<br>101 All<br>The profile shall have tabs for: Posts, Gatherings, Events Attended,<br>Store Listings, and Activity History.<br>102 Activity history shall include: liked posts, comments made, events  All<br>joined, gatherings created/joined, and store products listed.<br>103 We request the implementation of a 'City Founder of [City Name]'  City<br>Founder<br>profile label to recognize and highlight early contributors and local<br>pioneers.<br>**----- End of picture text -----**<br>


## **More Menu (MVP Phase 1)** 

|**ID**|**Requirement**|**Actor**|
|---|---|---|
|**104**|**The More menu shall include: My Tickets, Settings, Become a City**<br>**Founder (Check city avalabilety), Contact Support, and Terms &**<br>**Conditions.**|**All**|
|**105**|**Non-City-Founders shall be able to submit a City Founder**<br>**application from the More menu.**|**All**|
|**106**|**Settings shall allow: language change, account management**<br>**(email/password), notifcation preferences, account deletion, and**<br>**Logout.**|**All**|



## **Subscription & Payment (MVP Phase 1)** 

**==> picture [541 x 711] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>107 The system shall support a paid Member subscription with  Member<br>recurring billing (monthly and annual options).<br>108 Payment shall be processed through a secure payment gateway. System<br>109 The system shall handle subscription renewal, expiry, and  System<br>cancellation automatically.<br>110 Users shall receive a payment receipt via email after each  System<br>successful transaction.<br>111 The system shall send the user a push notification and an in-app  System<br>message before their subscription expires, clearly stating the exact<br>expiry date, so the user has time to renew.<br>112 When a subscription expires, the system shall immediately send  System<br>the user a notification informing them that their subscription has<br>ended and that they have a 1-week grace period before Member<br>privileges are revoked.<br>113 Member privileges shall remain active during the 1-week grace  System<br>period after expiry. If the user does not renew within this period,<br>privileges shall be fully revoked until renewal.<br>114 City Founders shall be able to view their earnings and revenue split  City<br>breakdown in their dashboard. Founder<br>115 The system shall allow users to select their preferred payment  Member /<br>method—either online pre-payment or cash payment—when  System<br>registering for or checking in at a paid event.<br>116 The application shall support a comprehensive and secure suite of  System<br>payment methods, including but not limited to major credit/debit<br>cards (Visa, Mastercard, American Express), prominent digital<br>wallets (Apple Pay, Google Pay), and physical cash-on-arrival.<br>**----- End of picture text -----**<br>


## **Trust Voting (MVP Phase 1)** 

**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>117 The system shall trigger a post-event trust vote prompt for all  System<br>attendees who were checked in (QR code scanned) at an event,<br>sent within 2 hours after the event's scheduled end time.<br>118 The vote prompt shall present two options: "Trusted" (positive)  All<br>and "Not Trusted" (negative), with an optional free-text comment<br>field (max 200 characters).<br>119 Each attendee may cast only one vote per event. Duplicate vote  System<br>attempts shall be rejected by the system.<br>120 Votes shall be accepted for a window of 48 hours after the event  System<br>ends. After this window, the voting prompt shall be dismissed<br>automatically.<br>121 The system shall calculate the percentage of positive votes (V)  System<br>from all votes cast for the event.<br>122 The system shall retrieve the City Founder's stored cumulative  System<br>trust score (S_prev) and cumulative vote count (W_prev), then<br>compute the new score using the weighted moving average<br>formula defined in this section.<br>123 The updated trust score (S_new) and updated cumulative vote  System<br>count shall be persisted immediately after the voting window<br>closes.<br>124 The City Founder's trust score shall be displayed as a percentage  System<br>(e.g., 87%) on their profile page, visible to all users.<br>125 The Admin Dashboard shall display each City Founder's current  Admin<br>trust score, total vote count, and a per-event vote breakdown<br>chart.<br>126 Admin<br>Admin shall be able to flag or investigate any event where the trust<br>score drops more than 20 percentage points below the Founder's<br>historical average.<br>127 City Founders shall NOT be able to view individual voter identities;  System<br>**----- End of picture text -----**<br>


**==> picture [541 x 167] intentionally omitted <==**

**----- Start of picture text -----**<br>
they may only see their aggregate score and the event-level vote<br>count.<br>128 Optional trust vote comments shall be reviewed by Admin only and  Admin<br>shall not be publicly visible.<br>129 A City Founder account shall require a minimum trust score of 40%  System<br>(after at least 10 cumulative votes) to remain active. Falling below<br>this threshold shall trigger an Admin review alert.<br>**----- End of picture text -----**<br>


## **Admin Dashboard** 

The Admin Dashboard is a web application accessible only to platform administrators. It provides full visibility and control over all MixedMiles data globally. 

## **Access & Authentication (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**130**|**The Admin Dashboard shall be accessible via a secure web URL, protected by**<br>**admin-only credentials.**|
|**131**|**Admin accounts shall support two-factor authentication (2FA).**|
|**132**|**All admin actions shall be logged in an audit trail (who changed what, and when).**|



## **City Founder Management (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**133**|**The admin shall be able to view a list of all City Founders across all countries**<br>**and cities.**|
|**134**|**The admin shall be able to view the full profle of each City Founder, including**<br>**their events, team, partners, and earnings.**|
|**135**|**The admin shall be able to add a new City Founder manually.**|
|**136**|**The admin shall be able to edit any feld of a City Founder's profle.**|
|**137**|**The admin shall be able to deactivate or permanently delete a City Founder**<br>**account.**|



## **Member & User Management (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**138**|**The admin shall be able to view all registered users (Members and Non-**<br>**Members).**|
|**139**|**The admin shall be able to search, flter, and sort users by country, city,**<br>**subscription status, and registration date.**|
|**140**|**The admin shall be able to edit, deactivate or delete any user account.**|



## **Event & Content Management (MVP Phase 1)** 

**==> picture [542 x 616] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>141 The admin shall be able to view all events across all cities and countries.<br>142 The admin shall be able to edit or delete any event on the platform.<br>143 The admin shall be able to view and moderate all posts and comments.<br>144 The admin shall be able to remove any post, comment, or media that violates<br>community guidelines.<br>145 The admin shall be able to remove any post, comment, or media that violates<br>community guidelines.<br>146 The admin shall be able to view all photos and videos uploaded by City<br>Founders to the Media Area, with filters by City Founder, city, date, and media<br>type (photo / video).<br>147 The admin shall be able to delete any photo or video uploaded by a City<br>Founder.<br>148 The admin shall be able to review pending membership applications that require<br>manual approval (non-expatriate applicants), and approve or reject each one.<br>The applicant shall be notified of the decision.<br>Partner (Guidebook) Management (MVP Phase 1)<br>ID Requirement<br>149 The admin shall be able to view, add, edit, and delete partner businesses from<br>the Guidebook.<br>**----- End of picture text -----**<br>


## **Analytics & Charts (MVP Phase 1)** 

**==> picture [541 x 504] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>150 The admin dashboard shall display charts and KPIs including: total users, active<br>Members, total events, total revenue, and revenue split breakdown.<br>151<br>The admin shall be able to filter all analytics by country, city, date range, and<br>user type.<br>152 The admin shall be able to view event attendance trends, subscription growth,<br>partner usage, and store activity over time.<br>153<br>The admin shall be able to export any report or dataset as a Excel file.<br>Store Management (MVP Phase 2)<br>ID Requirement<br>154 The admin shall be able to view all Store product listings across all users and<br>cities.<br>155<br>The admin shall be able to search and filter Store listings by category, city, user<br>type (Member / Non-Member), and date.<br>156 The admin shall be able to remove any Store product listing that violates<br>community guidelines.<br>**----- End of picture text -----**<br>


## **City Founder Dashboard** 

The City Founder Dashboard is a web application that City Founders use to manage their city community, events, team, and media. Access is granted after Admin approval. 

## **Getting Started — Eligibility Requirements (MVP Phase 1)** 

Before a City Founder can publish any Event, the following conditions must ALL be met (enforced by the system): 

**==> picture [541 x 210] intentionally omitted <==**

**----- Start of picture text -----**<br>
# Requirement Minimum<br>1 Partner businesses added to their Guidebook At least 10 partners<br>2 Public speakers confirmed in their team At least 2 public speakers<br>3 At least 1 content creator<br>Content creators confirmed in their team<br>4 Event frequency commitment per calendar  At least 3 events/month<br>month<br>**----- End of picture text -----**<br>


## **Note:** 

**The dashboard shall show the Founder their progress toward each requirement and prevent event publishing until all four are satisfied.** 

## **Partner (Guidebook) Management (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**157**|**City Founders shall be able to add new partner businesses to their Guidebook,**<br>**providing: business name, logo, discount percentage, description, category,**<br>**address, city, map link, social media links, and hours.**|
|**158**|**City Founders shall be able to edit or remove any of their partner entries.**|
|**159**|**The system shall prevent a City Founder from publishing events if they have**<br>**fewer than 10 active partners.**|



## **Event Management (MVP Phase 1)** 

**==> picture [541 x 638] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>160<br>City Founders shall be able to create a new event by filling in: event name,<br>description, date, time, region, place name, map link, ticket price, and cover<br>image.<br>161<br>City Founders shall be able to edit the following fields of an existing event<br>before it takes place: event name, description, date, time, and cover image.<br>Editing the ticket price or location is NOT allowed.<br>162 City Founders shall be able to delete an event.<br>163<br>When a City Founder edits any allowed field of an event, all users who have<br>joined or shown interest in that event shall receive a push notification informing<br>them of the update, specifying what was changed.<br>164 When a City Founder deletes an event, all users who have joined or purchased a<br>ticket for that event shall receive a push notification informing them that the<br>event has been cancelled.<br>165 City Founders shall be able to view the list of all their created events with status<br>(upcoming, ongoing, past).<br>166 City Founders shall be able to view the attendee list for each event.<br>167 City Founders shall be able to accept or reject join requests from user for each<br>event.<br>168 Upon approving a user join request, the system shall automatically send the<br>invitation (with QR code and event location) to the applicant via WhatsApp and<br>email, and make it accessible in the app.<br>169 The dashboard shall show a real-time nationality breakdown per event.<br>**----- End of picture text -----**<br>


## **Team Management (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**170**|**City Founders shall be able to view their current team members and their roles.**|
|**171**|**City Founders shall be able to add new team members, specifying: name, role**<br>**(Public Speaker / Content Creator / Other), photo, and bio.**|
|**172**|**City Founders shall be able to edit any team member's details.**|
|**173**|**City Founders shall be able to delete a team member, with the system enforcing**<br>**a minimum of 2 public speakers and 1 content creator at all times.**|
|**174**|**If a deletion would cause the team to fall below the minimum, the system shall**<br>**block the deletion and display an explanatory message.**|



## **Media Area (MVP Phase 1)** 

The Media Area is a dedicated media section within the City Founder Dashboard where Founders upload and manage event photos and videos. 

**==> picture [541 x 322] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>175 City Founders shall have access to a Media Area section in their dashboard.<br>176 City Founders shall be able to upload photos and videos to the Media Area.<br>177 Uploaded media shall be organized by event or album, which the Founder can<br>name and manage.<br>178<br>City Founders shall be able to delete any media file from the Media Area.<br>179 Media uploaded to the Media Area may optionally be published to the<br>community Feed or attached to an event gallery.<br>180<br>Supported formats: images (JPEG, PNG, WEBP) and videos (MP4, MOV). Max file<br>size: 500 MB per video, 20 MB per image.<br>**----- End of picture text -----**<br>


## **Community & Statistics (MVP Phase 1)** 

|**ID**|**Requirement**|
|---|---|
|**181**|**The City Founder dashboard shall display a summary of their community: total**<br>**Members following them, total events held, total attendees, and revenue**<br>**earned.**|
|**182**|**The dashboard shall show a revenue breakdown per event including ticket sales,**<br>**Member vs Non-Member split, and the Founder's earnings after the MixedMiles**<br>**commission.**|
|**183**|**City Founders shall be able to view their event attendee nationality breakdown**<br>**to accept or reject the event attendees.**|
|**184**|**City Founder team members (public speakers and content creators) shall be**<br>**able to log in to the City Founder Dashboard using their own credentials.**|
|**185**|**Team member access shall be limited to read-only views and sections relevant**<br>**to their role (e.g., event details, ea). They shall NOT have access to: fnancial**<br>**data, partner management, team management, event creation/deletion, or join**<br>**request approvals. Only the City Founder account holder has full dashboard**<br>**access.**|



## **Non-Functional Requirements** 

## **Performance** 

**==> picture [541 x 711] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>1 The app shall load the main Feed within 2 seconds on a standard 4G connection.<br>2 API response time for standard requests shall not exceed 500 ms under normal<br>load.<br>3<br>QR code scanning and membership verification shall complete within 2 seconds.<br>4 Ticket delivery via WhatsApp and email shall complete within 60 seconds of<br>payment confirmation.<br>5 The system shall support at least 20,000 concurrent users without performance<br>degradation.<br>Security<br>ID Requirement<br>6 All data in transit shall be encrypted using HTTPS / TLS 1.2 or higher.<br>7 User passwords shall be stored using a strong hashing algorithm (bcrypt or<br>Argon2).<br>8 All API endpoints shall require authentication (JWT or OAuth 2.0 tokens).<br>9 Ticket QR codes shall include a unique tamper-proof token validated server-<br>side.<br>10 Partner QR codes shall be validated server-side; the result (member / non-<br>member) shall never be calculated client-side only.<br>11 The system shall rate-limit QR scan attempts to prevent abuse (max 10<br>scans/minute per user).<br>12 Sensitive user data (payment info) shall never be stored on the device.<br>**----- End of picture text -----**<br>


**Usability** 

**==> picture [541 x 247] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>13 The app shall fully support English (LTR layout).<br>14 The UI shall comply with WCAG 2.1 AA accessibility guidelines (contrast ratios,<br>tap target sizes ≥ 44×44 pt).<br>15 First-time users shall be able to complete registration and explore the Feed<br>within 3 minutes.<br>16 All primary actions (join event, scan QR, create post) shall be reachable within 3<br>taps from any main screen.<br>**----- End of picture text -----**<br>


## **Reliability & Availability** 

**==> picture [542 x 228] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>17 The system shall target 99.5% uptime (≤ 43.8 hours downtime per year).<br>18<br>The app shall handle network interruptions gracefully, showing offline indicators<br>without crashing.<br>19<br>Critical data (tickets, user profile) shall be cached locally for offline viewing.<br>20 The backend shall perform automated daily backups of all user and transaction<br>data.<br>**----- End of picture text -----**<br>


## **Compatibility** 

**==> picture [541 x 210] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement<br>21 The app shall run on iOS 14 and above.<br>22 The app shall run on Android 8.0 (API 26) and above.<br>23 The UI shall be responsive and optimized for screen sizes from 4.7 inch to 6.7<br>inch phones.<br>24 The app shall comply with Apple App Store and Google Play Store guidelines.<br>**----- End of picture text -----**<br>


## **Scalability** 

|**ID**|**Requirement**|
|---|---|
|**25**|**The backend architecture shall be designed to scale horizontally to**<br>**accommodate user growth.**|
|**26**|**The partner QR code system shall support up to 10,000 partner businesses**<br>**without performance impact.**|
|**27**|**Media storage (images, attachments) shall use a scalable cloud storage service**<br>**(e.g., AWS S3 or equivalent).**|



**UI / UX — Screens & Flows Mobile App — Screen Inventory** 

**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
Screen Who Sees  Description<br>It<br>Splash  All Logo, slogan, brand colors. Auto-navigates after 1-2 s.<br>Screen<br>Login All Email/password + Google/Apple sign-in + forgot<br>password.<br>Register All Name, email, area, nationality, phone number, password,<br>ID or Passport photo. Leads to membership prompt.<br>Membership  New users Explains Member benefits. 'Subscribe Now' + 'Skip'.<br>Prompt<br>Onboarding  New users 3–5 illustrated feature slides. Skippable.<br>Slides<br>Home / Feed All Posts, events, gatherings. 'Create Gathering' button.<br>Likes & comments.<br>Post Detail All Full post view, likes, comment thread, replies.<br>Create Post Registered Image picker (up to 5), caption, optional location.<br>Create  Registered  Title, description, date/time, area, optional cover image,<br>Gathering max attendees (≤ 20). Accessible for Members who have<br>attended at least 1 events. Accessible for Non-Members<br>who have attended at least 3 events.<br>Gathering  All Info + Join button. Location hidden until joined.<br>Detail<br>Events List All Cards: name, date, time, location, price, image. Filter by<br>city/date.<br>Event Detail All Full event info. Join (Member) or Request (Non-<br>Member).<br>Payment  All Secure payment for paid event tickets.<br>Screen<br>**----- End of picture text -----**<br>


**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
Ticket /  All QR code ticket, place name, and map link. Delivered via<br>Invitation WhatsApp + email.<br>Guidebook  All<br>Partner list with discount %, category/city filters.<br>List<br>Partner  All Business info, map, hours, discount details.<br>Detail<br>Property  All Browse available properties for rent.<br>Listings<br>My Property  Member Create, edit, delete own property listing.<br>Listing<br>Store All Browse all product listings. Filterable by category, price,<br>city.<br>Store  All Full product info, seller contact, chat shortcut.<br>Product<br>Detail<br>Add Store  All  Product name, description, price, category, up to 5<br>Product  (registere photos, contact method. Non-Members limited to 1<br>d) listing.<br>My Store  Registered View, edit, delete own store product listings.<br>Listings<br>Chat List Registered Conversations list, unread badge.<br>Chat Detail Registered Real-time messages + image attachments.<br>Profile All Photo, bio, stats, Membership QR (Members), tabs: Posts<br>/ Gatherings / Events / History.<br>Edit Profile Registered Edit photo, name, bio.<br>My Tickets Registered List of ticket QR codes for purchased/claimed events.<br>More Menu All My Tickets, Settings, Become City Founder, Support,<br>**----- End of picture text -----**<br>


**==> picture [541 x 207] intentionally omitted <==**

**----- Start of picture text -----**<br>
T&C.<br>Settings Registered Account, notifications, language, delete account.<br>City Founder  Non-CF Application form reviewed by Admin.<br>Apply<br>Brand Studio City  Full brand customization panel: name, logo, icon, colors<br>Founder  (with live preview), splash screen, onboarding slides,<br>(approved welcome message, email header, support contact, T&C<br>) URL. Publish / Save Draft / Reset controls.<br>**----- End of picture text -----**<br>


## **Web Dashboards — Screen Summary** 

**==> picture [596 x 843] intentionally omitted <==**

**----- Start of picture text -----**<br>
Dashboar Screen / Section Description<br>d<br>Admin Overview / Home KPI cards + charts: users, events, revenue, Members.<br>Admin City Founders List, search, filter. Add / edit / delete Founders.<br>Admin Members / Users List with subscription status. Edit / deactivate.<br>Admin Events All events across all cities. Edit / delete.<br>Admin Guidebook /  All partners. Add / edit / delete. QR management.<br>Partners<br>Admin Store  All store products. Review, approve, remove listings.<br>Management<br>Admin Analytics Charts filtered by country, city, date range.<br>Admin Settings Admin account settings, 2FA, audit log.<br>City  Overview My community stats: Members, events, revenue,<br>Founder split.<br>City  Partners  Add / edit / delete partner businesses.<br>Founder (Guidebook)<br>City  Events Create / edit / delete events. View attendee list.<br>Founder<br>City  Join Requests Accept / reject Non-Member join requests per event.<br>Founder<br>City  Team Add / edit / delete team members (speakers,<br>Founder creators).<br>City  ea Upload / manage photos and videos by event/album.<br>Founder<br>City  Revenue Earnings per event, Member vs Non-Member split,<br>Founder commission.<br>**----- End of picture text -----**<br>


**8.3 Key User Flows** 

**Flow A — Member Redeems Partner Discount** 

1. Member opens their Profile and displays their Membership QR Code. 

2. Member shows (or the partner scans) the QR Code at the partner business. 

3. The partner's verification tool sends the QR token to the backend for validation. 4. Active Member → System confirms 'Active Member — Discount Applicable'. Redemption logged. 

5. Non-Member / Expired → System returns 'Not a Member — Discount Not Applicable'. 

## **Flow B — Non-Member Requests to Join Event** 

1. Non-Member taps 'Request to Join' on an event detail page. 

2. The request is sent to the City Founder's dashboard. 

3. City Founder reviews and clicks 'Accept' or 'Reject'. 

4. On acceptance: system sends invitation (with QR code + location) via WhatsApp and email. User can also open the invitation inside the app. 

5. User proceeds to the payment screen and completes payment. 6. Ticket QR code is generated and delivered. 

## **Flow C — City Founder Creates an Event** 

1. City Founder logs into the web dashboard. 

2. System checks eligibility: ≥10 partners, ≥2 speakers, ≥1 creator, 3 events/month commitment. 

3. If eligible: Founder fills in event name, description, date, time, area, location, price, image. 4. Founder publishes the event. It appears on the mobile app's Events list and Home page. 5. Founder monitors join requests and attendee nationality breakdown. 

## **Flow D — User Creates a Gathering** 

1. Any registered user (Member or Non-Member) taps **"Create Gathering"** on the Home page. 2. The system checks the user's eligibility: **Members** must have attended at least **1 event** . **Non-Members** must have attended at least **3 events** . 

3. If the user does not meet the requirement, the system displays an appropriate message and blocks the action: For Members: **"You need to attend at least 1 event before creating a Gathering."** For Non-Members: **"You need to attend at least 3 events before creating a Gathering."** 

4. If eligible, the user fills in: Title Description Date and Time Area Optional Cover Image Maximum Attendees (up to 20) 

5. The Gathering is published and appears in the Feed. 6. Other users can view, like, and comment on the Gathering. 

7. Joining a Gathering still requires an active Member subscription. 

8. The Gathering location is revealed only to Members who successfully join the Gathering. 

## **White Label** 

⚠ _**The architecture must support these capabilities for future implementation. No development is required at launch.**_ 

## **Overview** 

The "Powered by Mixed Miles" model allows independent expat communities around the world to operate under their own brand while using the Mixed Miles infrastructure. Each partner community maintains full brand identity (name, logo, colors) while benefiting from the platform's core technology, event tooling, membership management, and discount ecosystem. 

Branded communities appear as standalone products to end users but are managed centrally through the Mixed Miles admin layer. 

## **Concept & Branding** 

Partner communities operate under a co-branding model: 

- The community presents its own name and identity to members (e.g., "Jakarta Expats"). A subtle "Powered by Mixed Miles" attribution appears in the app footer, login screen, and partner-facing materials. 

- All backend operations, data storage, and compliance remain under Mixed Miles infrastructure. 

## **Example branded communities:** 

**==> picture [541 x 42] intentionally omitted <==**

**----- Start of picture text -----**<br>
Community Name City / Region Branding<br>**----- End of picture text -----**<br>


|**Community Name**|**City / Region**|**Branding**|
|---|---|---|
||||
|**Jakarta Expats**|**Jakarta, Indonesia**|**Jakarta Expats – Powered**<br>**by Mixed Miles**|
|**Singapore Expats**|**Singapore**|**Singapore Expats –**<br>**Powered by Mixed Miles**|
|**Expats in Bangkok**|**Bangkok, Thailand**|**Expats in Bangkok –**<br>**Powered by Mixed Miles**|



## **Features Available to White Label Communities** 

**==> picture [543 x 41] intentionally omitted <==**

**----- Start of picture text -----**<br>
Feature Description<br>**----- End of picture text -----**<br>


|**Feature**|**Description**|
|---|---|
|||
|**Event**<br>**Management**|**Full event creation, ticketing, QR codes, join request fows, and**<br>**attendee management via a branded City Founder dashboard.**|
|**Membership**<br>**Management**|**Subscription billing, member verifcation, QR-based discount**<br>**redemption, and membership lifecycle (renewal, grace period, expiry).**|
|**Community**<br>**Feed**|**Social posts, likes, comments, gatherings, and direct messaging — all**<br>**branded to the partner community.**|
|**QR Ticketing**|**Auto-generated, tamper-proof QR tickets delivered via WhatsApp,**<br>**email, and in-app — under the partner community's branding.**|
|**Discount**<br>**Management**|**Partner Guidebook with member QR verifcation, discount logging, and**<br>**partner business management.**|
|**Analytics**<br>**Dashboard**|**Community-specifc KPIs: members, events, revenue, attendance**<br>**trends, nationality breakdown, and subscription growth.**|
|**Housing**<br>**Module**|**City-scoped housing listings (Apartment for Rent, Room for Rent,**<br>**Looking for Roommate, Short-Term Stay) shared across all communities**<br>**in the same city.**|
|**Community**<br>**Exchange**|**City-scoped marketplace for second-hand goods, furniture, electronics,**<br>**and travel gear, shared across communities in the same city.**|



## **Revenue Model** 

White Label communities generate revenue for Mixed Miles through two mechanisms: 

- Monthly Subscription — The partner community pays a fixed monthly fee to use the Powered by Mixed Miles infrastructure. 

- Transaction Fee on Events — Mixed Miles collects a commission on each paid event ticket sold through the platform, consistent with the standard City Founder revenue split model. 

💡 _**Specific subscription pricing and commission rates are a commercial decision and are not defined in this specification.**_ 

## **Architecture Requirements** 

The current system architecture must be designed to accommodate White Label communities without requiring a rebuild. The following capabilities must be possible in the data model and backend from Day 1 of MVP development, even if they are not exposed in the UI at launch: 

## **Multi-Tenancy** 

- The system shall support multiple communities (tenants) operating independently within the same city. 

- Each community shall have its own members, events, team, and Guidebook. 

- Data isolation between communities must be enforced at the API layer. 

## **Shared City Assets** 

- Housing listings and Community Exchange listings shall be scoped to a city, not to an individual community. 

- All communities operating in the same city shall share the same housing and marketplace pool. 

- This prevents empty marketplaces in new communities and creates stronger network effects. 

_**Example: A new community "Expats in Amman" launched in 2027 would immediately have access to all existing Amman housing and marketplace listings created by Mixed Miles members or other Amman communities.**_ 

## **Shared Discount Ecosystem** 

- Partner businesses added to the Guidebook may be shared across communities in the same city. 

- The architecture shall support both community-exclusive partners and city-wide shared partners. 

## **Community Types** 

- The data model shall support different community types (e.g., general expat, nationalityspecific, interest-based) to allow future flexibility. 

## **Branding Layer** 

- The architecture shall support per-community theming variables (logo, primary color, community name) that can be applied to mobile app screens without requiring separate app builds. 

- "Powered by Mixed Miles" attribution placement shall be configurable per community. 

## **Functional Requirements** 

**==> picture [596 x 67] intentionally omitted <==**

**----- Start of picture text -----**<br>
ID Requirement Actor<br>**----- End of picture text -----**<br>


||**1**|**The system shall support the creation of White Label community accounts, each**|**Admin**||
|---|---|---|---|---|
|||**with a unique name, logo, and color scheme.**|||
||**2**|**Each White Label community shall have its own City Founder dashboard, members,**|**Admin**||
|||**events, and partner Guidebook.**|||
||**3**|**White Label communities in the same city shall share the city-level Housing and**|**System**||
|||**Community Exchange listings.**|||
||**4**|**The Admin Dashboard shall allow the platform operator to create, confgure,**|**Admin**||
|||**activate, and deactivate White Label communities.**|||
||**5**|**Admin shall be able to assign a monthly subscription fee and event commission rate**|**Admin**||
|||**to each White Label community.**|||
||**6**|**Each White Label community shall have isolated member data; members of one**|**System**||
|||**community shall not automatically have access to another community.**|||
||**7**|**The system shall generate revenue reports per White Label community, showing**|**Admin**||
|||**subscription fees collected and event commission earned.**|||
||**8**|**White Label community dashboards shall display the "Powered by Mixed Miles"**|**System**||
|||**attribution in a standardized location.**|||
||**9**|**The mobile app shall be capable of rendering community-specifc branding (name,**|**System**||
|||**logo, colors) dynamically without requiring a separate app binary.**|||
||**10**|**White Label communities shall use the same QR ticketing, membership verifcation,**|**System**||
|||**and discount redemption infrastructure as Mixed Miles core.**|||
||||||



